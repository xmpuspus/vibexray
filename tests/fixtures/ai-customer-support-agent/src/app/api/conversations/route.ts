import { db } from "@/lib/db";
import { conversations, customers } from "@/lib/db/schema";
import { desc, eq } from "drizzle-orm";
import { jsonError } from "@/lib/validation";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const status = searchParams.get("status");
    const limit = Math.min(Number(searchParams.get("limit") ?? 50), 100);

    const rows = await db
      .select({
        id: conversations.id,
        status: conversations.status,
        channel: conversations.channel,
        createdAt: conversations.createdAt,
        updatedAt: conversations.updatedAt,
        customerName: customers.name,
        customerEmail: customers.email,
      })
      .from(conversations)
      .leftJoin(customers, eq(conversations.customerId, customers.id))
      .where(status ? (eq(conversations.status, status as any)) : undefined)
      .orderBy(desc(conversations.updatedAt))
      .limit(limit);

    return Response.json({ conversations: rows });
  } catch (err) {
    console.error("[/api/conversations] error", err);
    return jsonError("Failed to load conversations", 500);
  }
}
