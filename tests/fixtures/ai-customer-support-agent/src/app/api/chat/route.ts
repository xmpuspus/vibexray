import { db } from "@/lib/db";
import { conversations, messages } from "@/lib/db/schema";
import { eq, asc } from "drizzle-orm";
import { chatRequestSchema, jsonError } from "@/lib/validation";
import { runAgent } from "@/lib/agent/agent";
import type { ChatMessageInput } from "@/lib/ai/types";

export const runtime = "nodejs";

/**
 * POST /api/chat
 * Body: { conversationId?: string, customerId?: string, message: string }
 *
 * Creates a conversation on first message if none is supplied, persists
 * the customer message, runs the AI agent (RAG + tools), persists the
 * assistant reply with its sources, and returns everything the UI needs
 * to render the turn.
 */
export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return jsonError("Invalid JSON body");
  }

  const parsed = chatRequestSchema.safeParse(body);
  if (!parsed.success) {
    return jsonError(parsed.error.issues.map((i) => i.message).join(", "));
  }
  const { message } = parsed.data;
  let { conversationId, customerId } = parsed.data;

  try {
    if (!conversationId) {
      const [convo] = await db
        .insert(conversations)
        .values({ customerId: customerId ?? null, status: "AI_HANDLING" })
        .returning();
      conversationId = convo.id;
    } else {
      const [existing] = await db.select().from(conversations).where(eq(conversations.id, conversationId));
      if (!existing) return jsonError("Conversation not found", 404);
      customerId = customerId ?? existing.customerId ?? undefined;
    }

    await db.insert(messages).values({
      conversationId,
      sender: "CUSTOMER",
      content: message,
    });

    const priorMessages = await db
      .select()
      .from(messages)
      .where(eq(messages.conversationId, conversationId))
      .orderBy(asc(messages.createdAt));

    const history: ChatMessageInput[] = priorMessages
      .slice(0, -1) // exclude the message we just inserted, it's passed separately
      .filter((m) => m.sender === "CUSTOMER" || m.sender === "ASSISTANT")
      .slice(-10) // sensible context window, not unbounded memory
      .map((m) => ({ role: m.sender === "CUSTOMER" ? "user" : "assistant", content: m.content }));

    const result = await runAgent({
      conversationId,
      customerId: customerId ?? null,
      userMessage: message,
      history,
    });

    await db.insert(messages).values({
      conversationId,
      sender: "ASSISTANT",
      content: result.answer,
      sources: result.sources,
    });

    await db
      .update(conversations)
      .set({
        status: result.escalated ? "ESCALATED" : "AI_HANDLING",
        updatedAt: new Date(),
      })
      .where(eq(conversations.id, conversationId));

    return Response.json({
      conversationId,
      answer: result.answer,
      sources: result.sources,
      escalated: result.escalated,
      toolCallsMade: result.toolCallsMade,
    });
  } catch (err) {
    console.error("[/api/chat] error", err);
    return jsonError("Something went wrong processing your message. Please try again.", 500);
  }
}
