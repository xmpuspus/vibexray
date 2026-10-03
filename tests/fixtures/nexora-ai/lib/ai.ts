import { openai } from "@ai-sdk/openai";
import { env } from "@/lib/env";
import { AppError } from "@/lib/errors";

export const EMBEDDING_DIMS = 1536;

/** pgvector literal, e.g. "[0.1,0.2,...]" — cast with ::vector in SQL. */
export const toVector = (v: number[]) => `[${v.join(",")}]`;

function requireKey() {
  if (!env().OPENAI_API_KEY)
    throw new AppError(503, "AI_NOT_CONFIGURED", "The AI provider is not configured. Set OPENAI_API_KEY (or AI_PROVIDER=mock for local dev).");
}

export async function getChatModel() {
  const c = env();
  if (c.AI_PROVIDER === "mock") return (await import("@/lib/ai-mock")).mockChatModel();
  requireKey();
  return openai(c.CHAT_MODEL);
}

export async function getEmbeddingModel() {
  const c = env();
  if (c.AI_PROVIDER === "mock") return (await import("@/lib/ai-mock")).mockEmbeddingModel();
  requireKey();
  return openai.textEmbeddingModel(c.EMBEDDING_MODEL);
}
