import { db } from "@/lib/db";
import { supportTickets, customers } from "@/lib/db/schema";
import { desc, eq } from "drizzle-orm";
import { createTicketSchema, jsonError } from "@/lib/validation";
import { requireAdmin } from "@/lib/require-admin";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status");

  const rows = await db
    .select({
      id: supportTickets.id,
      subject: supportTickets.subject,
      description: supportTickets.description,
      status: supportTickets.status,
      priority: supportTickets.priority,
      reason: supportTickets.reason,
      createdAt: supportTickets.createdAt,
      updatedAt: supportTickets.updatedAt,
      conversationId: supportTickets.conversationId,
      customerName: customers.name,
      customerEmail: customers.email,
    })
    .from(supportTickets)
    .leftJoin(customers, eq(supportTickets.customerId, customers.id))
    .where(status ? eq(supportTickets.status, status as any) : undefined)
    .orderBy(desc(supportTickets.createdAt));

  return Response.json({ tickets: rows });
}

export async function POST(req: Request) {
  const authError = await requireAdmin();
  if (authError) return authError;

  const body = await req.json();
  const parsed = createTicketSchema.safeParse(body);
  if (!parsed.success) return jsonError(parsed.error.issues.map((i) => i.message).join(", "));

  const [ticket] = await db.insert(supportTickets).values(parsed.data).returning();
  return Response.json({ ticket }, { status: 201 });
}
