import { z } from 'zod';
import type Anthropic from '@anthropic-ai/sdk';
import { config } from './config.ts';
import { articles, bookedSlots, orders, products, shipments, slotTimes } from './data.ts';
import { ToolError, TransientError } from './errors.ts';

export interface ToolContext {
  /** Park an action that changes customer data until the customer approves it in the UI. */
  requestConfirmation(tool: string, summary: string, execute: () => unknown): { actionId: string };
}

export interface ToolSpec<S extends z.ZodType = z.ZodType> {
  name: string;
  description: string;
  schema: S;
  timeoutMs?: number;
  retries?: number;
  run(input: z.infer<S>, ctx: ToolContext): unknown | Promise<unknown>;
}

const defineTool = <S extends z.ZodType>(spec: ToolSpec<S>) => spec as unknown as ToolSpec;

const RETURN_WINDOW_DAYS = 30;
const CARD_RETURN_SHIPPING = 6.95;

const orderId = z
  .string()
  .regex(/^[A-Za-z]\d{4}$/, 'Order numbers look like A1234')
  .transform((s) => s.toUpperCase())
  .describe('Order number, e.g. A1001');

const daysBetween = (from: string, to: string) =>
  Math.round((Date.parse(to) - Date.parse(from)) / 86_400_000);

const addDays = (date: string, days: number) =>
  new Date(Date.parse(date) + days * 86_400_000).toISOString().slice(0, 10);

const maskEmail = (email: string) => email.replace(/^(.).*(@.*)$/, '$1***$2');

function findOrder(id: string) {
  const order = orders.find((o) => o.id === id);
  if (!order) throw new ToolError(`No order ${id} exists. Ask the customer to double-check the order number.`);
  return order;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
// Simulates a flaky carrier API: the first request for a "-SLOW" parcel hangs past the timeout.
const carrierAttempts = new Map<string, number>();

export const tools: ToolSpec[] = [
  defineTool({
    name: 'lookup_order',
    description:
      'Get the status, items, dates and tracking number of an order. Use it before answering any question about a specific order.',
    schema: z.object({ order_id: orderId }),
    run: ({ order_id }) => {
      const order = findOrder(order_id);
      const total = order.items.reduce((sum, i) => sum + i.price * i.qty, 0);
      return {
        id: order.id,
        customer_first_name: order.customer.split(' ')[0],
        email: maskEmail(order.email),
        status: order.status,
        placed_at: order.placedAt,
        delivered_at: order.deliveredAt ?? null,
        tracking_number: order.trackingNumber ?? null,
        items: order.items,
        total_usd: total,
        return_window_ends: order.deliveredAt ? addDays(order.deliveredAt, RETURN_WINDOW_DAYS) : null,
      };
    },
  }),

  defineTool({
    name: 'track_shipment',
    description: 'Get carrier tracking events and the estimated delivery date for a tracking number from lookup_order.',
    schema: z.object({ tracking_number: z.string().min(4).describe('Tracking number, e.g. TRK-5501') }),
    timeoutMs: 1500,
    retries: 2,
    run: async ({ tracking_number }) => {
      const attempt = (carrierAttempts.get(tracking_number) ?? 0) + 1;
      carrierAttempts.set(tracking_number, attempt);
      await sleep(tracking_number.endsWith('-SLOW') && attempt === 1 ? 4000 : 120);
      const shipment = shipments[tracking_number];
      if (!shipment) throw new ToolError(`The carrier has no parcel with tracking number ${tracking_number}.`);
      return { tracking_number, ...shipment, latest: shipment.events.at(-1) };
    },
  }),

  defineTool({
    name: 'check_stock',
    description: 'Check price and stock by size or variant for a product, plus the restock date when sold out.',
    schema: z.object({
      product: z.string().min(2).describe('Product name or SKU, e.g. "Trail Runner 2" or "TR2"'),
      variant: z.string().optional().describe('Size or variant, e.g. "42" or "M". Omit to list all variants.'),
    }),
    run: ({ product, variant }) => {
      const q = product.toLowerCase();
      const match = products.find((p) => p.sku.toLowerCase() === q || p.name.toLowerCase().includes(q));
      if (!match) {
        throw new ToolError(`No product matches "${product}". Known products: ${products.map((p) => p.name).join(', ')}.`);
      }
      if (variant !== undefined) {
        const key = Object.keys(match.stock).find((k) => k.toLowerCase() === variant.toLowerCase());
        if (!key) throw new ToolError(`${match.name} has no variant "${variant}". Variants: ${Object.keys(match.stock).join(', ')}.`);
        const units = match.stock[key];
        return { sku: match.sku, name: match.name, price_usd: match.price, variant: key, in_stock: units > 0, units, restock_date: units > 0 ? null : match.restockDate ?? 'unknown' };
      }
      return { sku: match.sku, name: match.name, price_usd: match.price, stock: match.stock, restock_date: match.restockDate ?? null };
    },
  }),

  defineTool({
    name: 'search_help_center',
    description: 'Search store policies (returns, refunds, exchanges, shipping, warranty, cancellations). Quote the policy instead of guessing it.',
    schema: z.object({ query: z.string().min(3).describe('What to look for, e.g. "refund time"') }),
    run: ({ query }) => {
      const words = query.toLowerCase().split(/\W+/).filter((w) => w.length > 2);
      const scored = articles
        .map((a) => {
          const text = `${a.title} ${a.body}`.toLowerCase();
          return { a, score: words.filter((w) => text.includes(w)).length };
        })
        .filter((s) => s.score > 0)
        .sort((x, y) => y.score - x.score)
        .slice(0, 2);
      if (!scored.length) return { results: [], note: 'No matching article. Offer a callback with a human agent.' };
      return { results: scored.map(({ a }) => ({ id: a.id, title: a.title, text: a.body })) };
    },
  }),

  defineTool({
    name: 'create_return_request',
    description:
      'Prepare a return for one item of a delivered order. It does NOT create the return by itself: the customer must approve it in the chat. Check the order and the returns policy first.',
    schema: z.object({
      order_id: orderId,
      sku: z.string().describe('SKU of the item to return, from lookup_order'),
      reason: z.enum(['wrong_size', 'defective', 'not_as_described', 'changed_mind', 'other']),
      refund_method: z.enum(['card', 'store_credit']),
    }),
    run: ({ order_id, sku, reason, refund_method }, ctx) => {
      const order = findOrder(order_id);
      if (order.status !== 'delivered' || !order.deliveredAt) {
        throw new ToolError(`Order ${order.id} is "${order.status}", only delivered orders can be returned.`);
      }
      const age = daysBetween(order.deliveredAt, config.today);
      if (age > RETURN_WINDOW_DAYS) {
        throw new ToolError(
          `Order ${order.id} was delivered ${age} days ago, outside the ${RETURN_WINDOW_DAYS}-day return window. Warranty may still apply to defects.`,
        );
      }
      const item = order.items.find((i) => i.sku.toLowerCase() === sku.toLowerCase());
      if (!item) throw new ToolError(`Order ${order.id} has no item ${sku}. Items: ${order.items.map((i) => i.sku).join(', ')}.`);

      const shipping = refund_method === 'card' ? CARD_RETURN_SHIPPING : 0;
      const refund = Math.round((item.price * item.qty - shipping) * 100) / 100;
      const summary = `Return ${item.name} from order ${order.id} (${reason.replace('_', ' ')}), refund $${refund} to ${refund_method === 'card' ? 'card' : 'store credit'}`;
      const { actionId } = ctx.requestConfirmation('create_return_request', summary, () => {
        const returnId = `R-${order.id.slice(1)}-${item.sku}`;
        return {
          return_id: returnId,
          label_url: `https://returns.example.com/labels/${returnId}.pdf`,
          refund_usd: refund,
          refund_method,
          instructions: 'Print the label, pack the item unworn in its original box and drop it at any UPS point within 14 days.',
        };
      });
      return {
        status: 'awaiting_customer_approval',
        action_id: actionId,
        summary,
        note: 'The customer now sees Approve / Decline buttons. Do not say the return is created until a system note confirms it.',
      };
    },
  }),

  defineTool({
    name: 'get_callback_slots',
    description: 'List free phone-callback slots with a human support agent for a date.',
    schema: z.object({ date: z.iso.date().describe('Date as YYYY-MM-DD') }),
    run: ({ date }) => {
      if (date <= config.today) throw new ToolError(`Callbacks can be booked from tomorrow (${addDays(config.today, 1)}).`);
      return { date, free: slotTimes.filter((t) => !bookedSlots.has(`${date} ${t}`)) };
    },
  }),

  defineTool({
    name: 'book_callback',
    description: 'Book a phone callback with a human support agent. Needs a date, a free time slot and a phone number.',
    schema: z.object({
      date: z.iso.date().describe('Date as YYYY-MM-DD'),
      time: z.enum(slotTimes as [string, ...string[]]).describe('One of the fixed slot times'),
      phone: z.string().regex(/^\+?[\d\s()-]{7,20}$/, 'Phone number with country code, e.g. +1 555 0142'),
      topic: z.string().max(200).describe('Short reason for the call'),
    }),
    run: ({ date, time, phone, topic }) => {
      if (date <= config.today) throw new ToolError(`Callbacks can be booked from tomorrow (${addDays(config.today, 1)}).`);
      const key = `${date} ${time}`;
      if (bookedSlots.has(key)) {
        const free = slotTimes.filter((t) => !bookedSlots.has(`${date} ${t}`));
        throw new ToolError(`${time} on ${date} is already taken. Free slots that day: ${free.join(', ') || 'none'}.`);
      }
      bookedSlots.add(key);
      return { booking_id: `CB-${date.replaceAll('-', '')}-${time.replace(':', '')}`, date, time, phone, topic };
    },
  }),
];

export const toolByName = new Map(tools.map((t) => [t.name, t]));

/** Tool definitions in the Anthropic Messages API format, generated from the zod schemas. */
export function anthropicTools(): Anthropic.Tool[] {
  return tools.map((t) => {
    const { $schema: _ignored, ...schema } = z.toJSONSchema(t.schema, { io: 'input' }) as Record<string, unknown>;
    return { name: t.name, description: t.description, input_schema: schema as Anthropic.Tool.InputSchema };
  });
}

export { ToolError, TransientError };
