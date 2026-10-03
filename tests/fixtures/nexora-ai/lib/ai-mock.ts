// Offline stand-ins so the whole agent flow runs without an API key (AI_PROVIDER=mock).
// Embeddings: hashed bag-of-words. Chat model: a small rule-based "agent" that emits real tool calls,
// reads tool results on the next step, and answers from history — enough to exercise the full pipeline.
import type { LanguageModelV2StreamPart } from "@ai-sdk/provider";
import { MockEmbeddingModelV2, MockLanguageModelV2, simulateReadableStream } from "ai/test";
import { EMBEDDING_DIMS } from "@/lib/ai";

const STOP = new Set(["the", "and", "for", "are", "you", "your", "can", "how", "what", "with", "this", "that", "from", "have", "will", "our", "not"]);

function hash(s: string) {
  let h = 2166136261;
  for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return h >>> 0;
}

export function hashEmbedding(text: string): number[] {
  const vec = new Array<number>(EMBEDDING_DIMS).fill(0);
  for (const raw of text.toLowerCase().match(/[a-z0-9]+/g) ?? []) {
    const t = raw.replace(/(ing|ed|es|s)$/, "");
    if (t.length > 2 && !STOP.has(t)) vec[hash(t) % EMBEDDING_DIMS] += 1;
  }
  const norm = Math.sqrt(vec.reduce((a, b) => a + b * b, 0)) || 1;
  return vec.map((x) => x / norm);
}

export const mockEmbeddingModel = () =>
  new MockEmbeddingModelV2({
    maxEmbeddingsPerCall: 100,
    doEmbed: async ({ values }) => ({ embeddings: values.map((v) => hashEmbedding(String(v))) }),
  });

type Part = { type: string; text?: string; toolName?: string; output?: { type: string; value: unknown } };
type Msg = { role: string; content: unknown };
type Decision = { kind: "text"; text: string } | { kind: "tool"; name: string; input: unknown };

const parts = (m: Msg): Part[] => (Array.isArray(m.content) ? (m.content as Part[]) : []);
const REFUSAL = "I can't help with that. I can't share internal instructions or bypass my rules, but I'm happy to help with your order, your account, or a support question.";

function kbAnswer(system: string): string {
  const kb = system.split("<knowledge_base>\n")[1] ?? ""; // only the retrieved section, not the rules above it
  if (kb.startsWith("NO_RELEVANT_DOCUMENTS"))
    return "I don't have information about that in our help articles, so I don't want to guess. I can connect you with a human agent who can help — would you like that?";
  const first = kb.match(/^\[1\] [^\n]*\n([\s\S]*?)(?:\n\n\[2\]|\n<\/knowledge_base>)/)?.[1] ?? "";
  const excerpt = first.replace(/^#+\s.*\n?/gm, "").replace(/\s+/g, " ").trim().match(/^(?:.+?[.!?](?:\s|$)){1,2}/)?.[0].trim() ?? "";
  return `Here's what our help articles say: ${excerpt} [1]`;
}

function summarizeToolResult(toolName: string, output: { type: string; value: unknown }): string {
  if (output.type !== "json") return "I couldn't complete that request because the lookup failed. I can open a support ticket so a human can help — would you like that?";
  const v = output.value as Record<string, any>;
  if (!v.ok) return `I couldn't complete that: ${v.message} I can open a support ticket so a human can look into it — would you like that?`;
  if (toolName === "getOrderStatus")
    return `Order ${v.orderNumber} is ${String(v.status).toLowerCase()}.${v.trackingNumber ? ` Carrier: ${v.carrier}, tracking number ${v.trackingNumber}.` : ""}`;
  if (toolName === "getCustomerAccount")
    return `You're signed in as ${v.name} (${v.email}). You have ${v.recentOrders.length} recent order(s) and ${v.openTickets} open ticket(s).`;
  if (toolName === "createSupportTicket")
    return `${v.duplicate ? "You already have a matching open ticket" : "I've created a ticket"}: ${v.ticketNumber}. Our support team will follow up.`;
  return "Done.";
}

function decide(prompt: Msg[]): Decision {
  const system = String(prompt.find((m) => m.role === "system")?.content ?? "");
  const last = prompt[prompt.length - 1];

  // Step 2 of a tool round-trip: turn the tool result into an answer.
  if (last.role === "tool") {
    const r = parts(last).find((p) => p.type === "tool-result");
    return { kind: "text", text: summarizeToolResult(r?.toolName ?? "", r?.output ?? { type: "error-text", value: "" }) };
  }

  const userTexts = prompt.filter((m) => m.role === "user").map((m) => parts(m).map((p) => p.text ?? "").join(""));
  const text = userTexts.at(-1) ?? "";
  const priorTools = prompt.filter((m) => m.role === "tool").flatMap(parts).filter((p) => p.type === "tool-result");

  if (system.includes("PROMPT INJECTION WARNING")) return { kind: "text", text: REFUSAL };
  if (text.includes("[invalid-args-test]")) return { kind: "tool", name: "getOrderStatus", input: { orderId: "???" } };
  const order = text.match(/\bSA-\d{3,}\b/i)?.[0];
  if (order) return { kind: "tool", name: "getOrderStatus", input: { orderId: order } };
  if (/(create|open|raise) (a )?(support )?ticket|human agent|talk to (a )?(human|person|agent)/i.test(text))
    return { kind: "tool", name: "createSupportTicket", input: { subject: "Customer requested human support", description: `Customer message: ${text}` } };
  if (/tracking/i.test(text)) {
    const prev = priorTools.map((p) => p.output?.value as Record<string, any>).reverse().find((v) => v?.trackingNumber);
    if (prev) return { kind: "text", text: `From the order we looked up earlier (${prev.orderNumber}), the tracking number is ${prev.trackingNumber} with ${prev.carrier}.` };
  }
  if (/first question|first message/i.test(text)) return { kind: "text", text: `Your first message in this conversation was: "${userTexts[0]}".` };
  if (/\b(my account|account details|profile|who am i)\b/i.test(text)) return { kind: "tool", name: "getCustomerAccount", input: {} };
  return { kind: "text", text: kbAnswer(system) };
}

const usage = { inputTokens: 0, outputTokens: 0, totalTokens: 0 };
const callId = () => `call_${crypto.randomUUID().slice(0, 8)}`;

export const mockChatModel = () =>
  new MockLanguageModelV2({
    // streaming (used by the chat route)
    doStream: async ({ prompt }) => {
      const d = decide(prompt as unknown as Msg[]);
      const chunks: LanguageModelV2StreamPart[] =
        d.kind === "tool"
          ? [
              { type: "stream-start", warnings: [] },
              { type: "tool-call", toolCallId: callId(), toolName: d.name, input: JSON.stringify(d.input) },
              { type: "finish", finishReason: "tool-calls", usage },
            ]
          : [
              { type: "stream-start", warnings: [] },
              { type: "text-start", id: "t1" },
              ...d.text.split(/(?<=\s)/).map((delta) => ({ type: "text-delta" as const, id: "t1", delta })),
              { type: "text-end", id: "t1" },
              { type: "finish", finishReason: "stop", usage },
            ];
      return { stream: simulateReadableStream({ chunkDelayInMs: Number(process.env.MOCK_CHUNK_DELAY_MS ?? 20), chunks }) };
    },
    // non-streaming (used by the evaluation runner)
    doGenerate: async ({ prompt }) => {
      const d = decide(prompt as unknown as Msg[]);
      return d.kind === "tool"
        ? { content: [{ type: "tool-call" as const, toolCallId: callId(), toolName: d.name, input: JSON.stringify(d.input) }], finishReason: "tool-calls" as const, usage, warnings: [] }
        : { content: [{ type: "text" as const, text: d.text }], finishReason: "stop" as const, usage, warnings: [] };
    },
  });
