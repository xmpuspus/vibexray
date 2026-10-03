import { db } from "@/lib/db";
import { customers, orders, orderItems, products, supportTickets, conversations } from "@/lib/db/schema";
import { eq, ilike, or, sql } from "drizzle-orm";
import type { ToolDefinition } from "@/lib/ai/types";

export interface ToolContext {
  conversationId: string;
  customerId: string | null;
}

export interface ToolResult {
  ok: boolean;
  data: Record<string, unknown>;
}

export type ToolHandler = (args: Record<string, unknown>, ctx: ToolContext) => Promise<ToolResult>;

// ---------- Tool: get_order_status ----------
const getOrderStatus: ToolHandler = async (args) => {
  const orderIdRaw = String(args.orderId ?? "").trim();
  if (!orderIdRaw) return { ok: false, data: { error: "orderId is required" } };

  // Accept either the bare number ("1045") or full order number ("ORD-1045").
  const candidate = orderIdRaw.toUpperCase().startsWith("ORD-")
    ? orderIdRaw.toUpperCase()
    : `ORD-${orderIdRaw}`;

  const [order] = await db
    .select()
    .from(orders)
    .where(or(eq(orders.orderNumber, candidate), eq(orders.orderNumber, orderIdRaw)));

  if (!order) {
    return { ok: false, data: { error: `No order found matching "${orderIdRaw}"` } };
  }

  return {
    ok: true,
    data: {
      orderNumber: order.orderNumber,
      status: order.status,
      total: order.total,
      placedAt: order.placedAt.toISOString().slice(0, 10),
      eta: order.eta ? order.eta.toISOString().slice(0, 10) : null,
      trackingNo: order.trackingNo,
    },
  };
};

// ---------- Tool: get_customer_info ----------
const getCustomerInfo: ToolHandler = async (args, ctx) => {
  const customerId = String(args.customerId ?? ctx.customerId ?? "").trim();
  if (!customerId) return { ok: false, data: { error: "customerId is required" } };

  const [customer] = await db.select().from(customers).where(eq(customers.id, customerId));
  if (!customer) return { ok: false, data: { error: "Customer not found" } };

  const customerOrders = await db.select().from(orders).where(eq(orders.customerId, customerId));

  return {
    ok: true,
    data: {
      name: customer.name,
      email: customer.email,
      totalOrders: customerOrders.length,
      memberSince: customer.createdAt.toISOString().slice(0, 10),
    },
  };
};

// ---------- Tool: search_products ----------
const searchProducts: ToolHandler = async (args) => {
  const query = String(args.query ?? "").trim();
  if (!query) return { ok: false, data: { error: "query is required" } };

  const terms = query
    .toLowerCase()
    .split(/\s+/)
    .filter((w) => w.length > 2)
    .slice(0, 5);

  if (terms.length === 0) {
    return { ok: true, data: { results: [] } };
  }

  const conditions = terms.flatMap((t) => [
    ilike(products.name, `%${t}%`),
    ilike(products.category, `%${t}%`),
    ilike(products.description, `%${t}%`),
  ]);

  const results = await db
    .select()
    .from(products)
    .where(or(...conditions))
    .limit(5);

  return {
    ok: true,
    data: {
      results: results.map((p) => ({
        id: p.id,
        name: p.name,
        category: p.category,
        price: p.price,
        stock: p.stock,
      })),
    },
  };
};

// ---------- Tool: check_product_availability ----------
const checkProductAvailability: ToolHandler = async (args) => {
  const productId = args.productId ? String(args.productId) : null;
  const query = args.query ? String(args.query) : null;

  let product;
  if (productId) {
    [product] = await db.select().from(products).where(eq(products.id, productId));
  } else if (query) {
    const terms = query.toLowerCase().split(/\s+/).filter((w) => w.length > 2);
    if (terms.length > 0) {
      [product] = await db
        .select()
        .from(products)
        .where(or(...terms.map((t) => ilike(products.name, `%${t}%`))))
        .limit(1);
    }
  }

  if (!product) return { ok: false, data: { error: "Product not found" } };

  return {
    ok: true,
    data: { id: product.id, name: product.name, stock: product.stock, price: product.price },
  };
};

// ---------- Tool: create_support_ticket ----------
const createSupportTicket: ToolHandler = async (args, ctx) => {
  const issue = String(args.issue ?? "").trim();
  if (!issue) return { ok: false, data: { error: "issue is required" } };

  const priority = ["LOW", "MEDIUM", "HIGH", "URGENT"].includes(String(args.priority))
    ? (args.priority as "LOW" | "MEDIUM" | "HIGH" | "URGENT")
    : "MEDIUM";

  const [ticket] = await db
    .insert(supportTickets)
    .values({
      conversationId: ctx.conversationId,
      customerId: ctx.customerId,
      subject: issue.slice(0, 120),
      description: issue,
      reason: "Created by AI agent from conversation",
      priority,
      status: "OPEN",
    })
    .returning();

  return { ok: true, data: { ticketId: ticket.id, status: ticket.status, priority: ticket.priority } };
};

// ---------- Tool: request_human_handoff ----------
const requestHumanHandoff: ToolHandler = async (args, ctx) => {
  const reason = String(args.reason ?? "Customer requested a human agent").trim();

  await db
    .update(conversations)
    .set({ status: "ESCALATED", updatedAt: new Date() })
    .where(eq(conversations.id, ctx.conversationId));

  const [ticket] = await db
    .insert(supportTickets)
    .values({
      conversationId: ctx.conversationId,
      customerId: ctx.customerId,
      subject: "Escalation: " + reason.slice(0, 100),
      description: reason,
      reason,
      priority: "HIGH",
      status: "OPEN",
    })
    .returning();

  return { ok: true, data: { escalated: true, ticketId: ticket.id, reason } };
};

export const TOOL_DEFINITIONS: ToolDefinition[] = [
  {
    name: "get_order_status",
    description: "Look up the status, ETA, and tracking info for a customer order by order number or ID.",
    parameters: {
      type: "object",
      properties: { orderId: { type: "string", description: "Order number, e.g. '1045' or 'ORD-1045'" } },
      required: ["orderId"],
    },
  },
  {
    name: "get_customer_info",
    description: "Look up basic account info for a customer.",
    parameters: {
      type: "object",
      properties: { customerId: { type: "string" } },
      required: [],
    },
  },
  {
    name: "search_products",
    description: "Search the product catalog by keyword, category, or name.",
    parameters: {
      type: "object",
      properties: { query: { type: "string" } },
      required: ["query"],
    },
  },
  {
    name: "check_product_availability",
    description: "Check current stock level for a specific product.",
    parameters: {
      type: "object",
      properties: {
        productId: { type: "string" },
        query: { type: "string", description: "Product name if productId is unknown" },
      },
      required: [],
    },
  },
  {
    name: "create_support_ticket",
    description: "File a support ticket for an issue that needs manual follow-up (damage, refund request, complaint).",
    parameters: {
      type: "object",
      properties: {
        issue: { type: "string" },
        priority: { type: "string", enum: ["LOW", "MEDIUM", "HIGH", "URGENT"] },
      },
      required: ["issue"],
    },
  },
  {
    name: "request_human_handoff",
    description: "Escalate the conversation to a human support agent.",
    parameters: {
      type: "object",
      properties: { reason: { type: "string" } },
      required: ["reason"],
    },
  },
];

export const TOOL_HANDLERS: Record<string, ToolHandler> = {
  get_order_status: getOrderStatus,
  get_customer_info: getCustomerInfo,
  search_products: searchProducts,
  check_product_availability: checkProductAvailability,
  create_support_ticket: createSupportTicket,
  request_human_handoff: requestHumanHandoff,
};
