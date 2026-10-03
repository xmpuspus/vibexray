import { convertToModelMessages, createUIMessageStreamResponse, stepCountIs, streamText } from "ai";
import { db } from "@/lib/db";
import { getChatModel } from "@/lib/ai";
import { getCurrentUser } from "@/lib/auth";
import { loadRecentMessages, toChatMessage } from "@/lib/chat-history";
import { env } from "@/lib/env";
import { AppError, handleError, logError } from "@/lib/errors";
import { rateLimit } from "@/lib/rate-limit";
import { buildSystemPrompt } from "@/lib/rag/prompt";
import { retrieve, toSources } from "@/lib/rag/retrieve";
import { looksLikeInjection, redactSecrets } from "@/lib/security";
import { createTools } from "@/lib/tools";
import { chatRequestSchema } from "@/lib/validations";
import type { ChatMessage } from "@/types";

export const maxDuration = 60;

export async function POST(req: Request) {
  const startedAt = Date.now();
  try {
    const user = await getCurrentUser();
    rateLimit(`chat:${user.id}`, 20);
    const { id, message } = chatRequestSchema.parse(await req.json());
    const text = message.parts.map((p) => p.text).join("\n");
    const model = await getChatModel(); // fails fast (503) if the provider isn't configured

    // Create the conversation on first message; never expose someone else's.
    const existing = await db.conversation.findUnique({ where: { id }, select: { userId: true } });
    if (existing && existing.userId !== user.id) throw new AppError(404, "NOT_FOUND", "Conversation not found.");

    const history = existing ? await loadRecentMessages(id, 20) : [];
    const injectionFlagged = looksLikeInjection(text);
    if (injectionFlagged) console.warn(`[security] possible prompt injection from user ${user.id}`);

    // Very short follow-ups ("and for damaged items?") only make sense with the previous question attached.
    const previousQuestion = [...history].reverse().find((m) => m.role === "USER")?.content;
    const query = previousQuestion && text.split(/\s+/).length <= 4 ? `${previousQuestion}\n${text}` : text;

    // Retrieve BEFORE saving anything: if the knowledge base is down the request fails cleanly, with no orphaned message.
    const chunks = await retrieve(query);
    const sources = toSources(chunks);

    if (!existing) await db.conversation.create({ data: { id, userId: user.id, title: text.slice(0, 60) } });
    await db.message.create({ data: { conversationId: id, role: "USER", content: text } });

    const messages: ChatMessage[] = [
      ...history.map(toChatMessage),
      { id: crypto.randomUUID(), role: "user", parts: [{ type: "text", text }] },
    ];

    const result = streamText({
      model,
      system: buildSystemPrompt(chunks, { customerName: user.name, injectionFlagged }),
      messages: convertToModelMessages(messages),
      tools: createTools({ userId: user.id, conversationId: id }), // bound to the session user, not to anything the model says
      stopWhen: stepCountIs(5), // call tool(s) → read results → answer
      temperature: 0.2,
    });
    const uiStream = result.toUIMessageStream({
      originalMessages: messages,
      messageMetadata: ({ part }) => (part.type === "start" ? { sources } : undefined),
      onFinish: async ({ responseMessage }) => {
        const parts = responseMessage.parts.map((p) => (p.type === "text" ? { ...p, text: redactSecrets(p.text) } : p));
        const content = parts.map((p) => (p.type === "text" ? p.text : "")).join("");
        if (!parts.length) return;
        await db.message.create({
          data: { conversationId: id, role: "ASSISTANT", content, metadata: JSON.parse(JSON.stringify({
              sources,
              parts,
              trace: { query, retrieved: chunks.length, topScore: chunks[0]?.score ?? null, latencyMs: Date.now() - startedAt, injectionFlagged, model: env().AI_PROVIDER === "mock" ? "mock" : env().CHAT_MODEL },
            })),
          },
        });
        await db.conversation.update({ where: { id }, data: { updatedAt: new Date() } });
      },
      onError: (err) => {
        logError("[chat] stream error:", err);
        return "The assistant hit an error. Please try again.";
      },
    });

    // Send one branch to the browser and drain the other on the server, so generation, tool calls and
    // saving finish even if the user closes the tab mid-answer.
    const [toClient, toServer] = uiStream.tee();
    void toServer.pipeTo(new WritableStream()).catch(() => {});
    return createUIMessageStreamResponse({ stream: toClient });
  } catch (err) {
    return handleError(err);
  }
}
