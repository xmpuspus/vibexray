/**
 * tools.ts — The six callable tools the agent can invoke.
 *
 * Every function returns { success, data?, error? } so the agent loop
 * never crashes on a failed DB call — it receives a structured error it
 * can reason about and relay to the customer.
 */

import { PrismaClient } from '@prisma/client';
import { ToolResult } from '../types';

const prisma = new PrismaClient();

// ── 1. get_order_by_id ───────────────────────────────────────────────────────

export async function get_order_by_id(orderId: string): Promise<ToolResult> {
  try {
    const order = await prisma.order.findUnique({
      where: { id: orderId },
      include: {
        customer: { select: { id: true, email: true, name: true } },
        refund: true,
      },
    });

    if (!order) {
      return { success: false, error: `Order "${orderId}" not found.` };
    }

    return { success: true, data: order };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return { success: false, error: `Database error: ${msg}` };
  }
}

// ── 2. get_orders_by_customer ────────────────────────────────────────────────

export async function get_orders_by_customer(email: string): Promise<ToolResult> {
  try {
    const customer = await prisma.customer.findUnique({
      where: { email },
      include: {
        orders: {
          include: { refund: true },
          orderBy: { createdAt: 'desc' },
        },
      },
    });

    if (!customer) {
      return {
        success: false,
        error: `No customer found with email "${email}". Please verify the address.`,
      };
    }

    const { passwordHash: _pw, ...safeCustomer } = customer;
    return {
      success: true,
      data: {
        customer: safeCustomer,
        orders: customer.orders,
        orderCount: customer.orders.length,
      },
    };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return { success: false, error: `Database error: ${msg}` };
  }
}

// ── 3. update_order_status ───────────────────────────────────────────────────

type ValidStatus =
  | 'PENDING'
  | 'CONFIRMED'
  | 'PREPARING'
  | 'OUT_FOR_DELIVERY'
  | 'DELIVERED'
  | 'CANCELLED'
  | 'REFUNDED';

const VALID_STATUSES: ValidStatus[] = [
  'PENDING', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY',
  'DELIVERED', 'CANCELLED', 'REFUNDED',
];

export async function update_order_status(
  orderId: string,
  status: string,
): Promise<ToolResult> {
  if (!VALID_STATUSES.includes(status as ValidStatus)) {
    return {
      success: false,
      error: `Invalid status "${status}". Must be one of: ${VALID_STATUSES.join(', ')}.`,
    };
  }

  try {
    const order = await prisma.order.update({
      where: { id: orderId },
      data: { status: status as ValidStatus },
    });
    return { success: true, data: order };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes('Record to update not found')) {
      return { success: false, error: `Order "${orderId}" not found.` };
    }
    return { success: false, error: `Database error: ${msg}` };
  }
}

// ── 4. issue_refund ──────────────────────────────────────────────────────────

export async function issue_refund(
  orderId: string,
  amount: number,
  reason: string,
): Promise<ToolResult> {
  try {
    // Pre-check: does the order exist and is it already refunded?
    const existing = await prisma.order.findUnique({
      where: { id: orderId },
      include: { refund: true },
    });

    if (!existing) {
      return { success: false, error: `Order "${orderId}" not found.` };
    }

    if (existing.refund) {
      return {
        success: false,
        error: `Order "${orderId}" has already been refunded on ${existing.refund.createdAt.toISOString()}.`,
      };
    }

    if (existing.status === 'REFUNDED') {
      return {
        success: false,
        error: `Order "${orderId}" is already in REFUNDED status.`,
      };
    }

    // Atomic transaction: create refund record + update order status
    const refund = await prisma.$transaction(async (tx) => {
      const r = await tx.refund.create({
        data: { orderId, amount, reason },
      });
      await tx.order.update({
        where: { id: orderId },
        data: { status: 'REFUNDED' },
      });
      return r;
    });

    return {
      success: true,
      data: {
        refundId: refund.id,
        orderId,
        amount: refund.amount,
        reason: refund.reason,
        createdAt: refund.createdAt,
        message: `Refund of $${Number(amount).toFixed(2)} successfully issued for order ${orderId}.`,
      },
    };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return { success: false, error: `Database error: ${msg}` };
  }
}

// ── 5. get_menu ──────────────────────────────────────────────────────────────

export async function get_menu(): Promise<ToolResult> {
  try {
    const items = await prisma.menuItem.findMany({
      where: { available: true },
      orderBy: [{ category: 'asc' }, { name: 'asc' }],
    });

    // Group by category for cleaner agent output
    const grouped = items.reduce<Record<string, typeof items>>((acc, item) => {
      if (!acc[item.category]) acc[item.category] = [];
      acc[item.category].push(item);
      return acc;
    }, {});

    return { success: true, data: { items, grouped, count: items.length } };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return { success: false, error: `Database error: ${msg}` };
  }
}

// ── 6. escalate_to_human ─────────────────────────────────────────────────────

export async function escalate_to_human(reason: string): Promise<ToolResult> {
  try {
    const ticketNumber = `TKT-${Date.now()}-${Math.floor(Math.random() * 1000)
      .toString()
      .padStart(3, '0')}`;

    await prisma.escalation.create({
      data: { reason, ticketNumber },
    });

    return {
      success: true,
      data: {
        ticketNumber,
        message:
          `Your issue has been escalated to our human support team. ` +
          `Your ticket number is **${ticketNumber}**. ` +
          `A team member will contact you within 2 business hours.`,
      },
    };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return { success: false, error: `Database error: ${msg}` };
  }
}

// Named dispatch function used by the ReAct loop
export async function dispatchTool(
  name: string,
  input: Record<string, unknown>,
): Promise<ToolResult> {
  switch (name) {
    case 'get_order_by_id':
      return get_order_by_id(input['orderId'] as string);
    case 'get_orders_by_customer':
      return get_orders_by_customer(input['email'] as string);
    case 'update_order_status':
      return update_order_status(input['orderId'] as string, input['status'] as string);
    case 'issue_refund':
      return issue_refund(input['orderId'] as string, input['amount'] as number, input['reason'] as string);
    case 'get_menu':
      return get_menu();
    case 'escalate_to_human':
      return escalate_to_human(input['reason'] as string);
    default:
      return { success: false, error: `Unknown tool: "${name}"` };
  }
}
