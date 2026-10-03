/**
 * react-loop.ts — ReAct agent loop powered by Groq (free tier).
 *
 * Uses the OpenAI-compatible client pointed at Groq's API.
 * Model: llama-3.3-70b-versatile — supports tool calling, free tier.
 *
 * Flow per turn:
 *   1. Send full message history + system prompt to Groq
 *   2. If finish_reason === 'tool_calls' → execute tools, append results, loop
 *   3. If finish_reason === 'stop'       → return final text to caller
 */

import OpenAI from 'openai';
import { dispatchTool } from './tools';
import { ToolCallLog, ToolResult } from '../types';

const client = new OpenAI({
  apiKey: process.env.GROQ_API_KEY,
  baseURL: 'https://api.groq.com/openai/v1',
});

const MODEL = 'llama-3.3-70b-versatile';

// ── System prompt ────────────────────────────────────────────────────────────

const SYSTEM_PROMPT = `You are SliceIQ, a warm and efficient customer support agent for a pizza delivery service.

You help customers with:
- Tracking orders ("where is my order?")
- Refund requests ("I want a refund")
- Wrong order received ("I got the wrong pizza")
- Order cancellation ("cancel my order")
- Menu inquiries ("what pizzas do you have?")
- Complaints ("my pizza was cold / late")
- Escalating unresolvable issues to a human agent

## Guidelines
- Always look up real data using your tools — never fabricate order IDs, statuses, or prices.
- When a customer mentions their email, call get_orders_by_customer immediately to identify them.
- Before issuing a refund, confirm the amount and reason with the customer.
- For cancellations: only cancel orders with status PENDING or CONFIRMED; politely explain if it is too late.
- For complaints about cold/late pizza, offer a refund proactively.
- Escalate to a human agent only if you truly cannot resolve the issue.
- Keep responses concise, empathetic, and professional.`;

// ── Tool definitions (OpenAI function-calling format) ────────────────────────

const TOOL_DEFINITIONS: OpenAI.Chat.ChatCompletionTool[] = [
  {
    type: 'function',
    function: {
      name: 'get_order_by_id',
      description: 'Fetch a single order with all fields (items, status, total, refund) by order ID.',
      parameters: {
        type: 'object',
        properties: {
          orderId: { type: 'string', description: 'The unique order ID' },
        },
        required: ['orderId'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_orders_by_customer',
      description: 'Fetch all orders for a customer by their email address.',
      parameters: {
        type: 'object',
        properties: {
          email: { type: 'string', description: "Customer's email address" },
        },
        required: ['email'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'update_order_status',
      description: 'Update the status of an order. Use for cancellations.',
      parameters: {
        type: 'object',
        properties: {
          orderId: { type: 'string' },
          status: {
            type: 'string',
            enum: ['PENDING', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED', 'REFUNDED'],
          },
        },
        required: ['orderId', 'status'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'issue_refund',
      description: 'Create a Refund record and set order status to REFUNDED. Only call after explicit customer confirmation.',
      parameters: {
        type: 'object',
        properties: {
          orderId: { type: 'string' },
          amount: { type: 'number', description: 'Refund amount in USD' },
          reason: { type: 'string' },
        },
        required: ['orderId', 'amount', 'reason'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_menu',
      description: 'Return the full menu grouped by category.',
      parameters: {
        type: 'object',
        properties: {},
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'escalate_to_human',
      description: 'Log escalation and return a ticket number. Use only when truly unresolvable.',
      parameters: {
        type: 'object',
        properties: {
          reason: { type: 'string', description: 'Why the issue needs a human' },
        },
        required: ['reason'],
      },
    },
  },
];

// ── Types ────────────────────────────────────────────────────────────────────

export interface ConversationMessage {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_call_id?: string;      // required when role === 'tool'
  tool_calls?: OpenAI.Chat.ChatCompletionMessageToolCall[];  // on assistant messages
}

export interface AgentTurn {
  message: string;
  toolCallLogs: ToolCallLog[];
}

// ── Main loop ────────────────────────────────────────────────────────────────

export async function runAgentLoop(
  history: ConversationMessage[],
  userMessage: string,
  onToolCall?: (log: ToolCallLog) => void,
): Promise<AgentTurn> {
  const messages: ConversationMessage[] = [
    ...history,
    { role: 'user', content: userMessage },
  ];

  const toolCallLogs: ToolCallLog[] = [];
  let finalMessage = '';
  let iterations = 0;
  const MAX_ITERATIONS = 10;

  while (iterations < MAX_ITERATIONS) {
    iterations++;

    const response = await client.chat.completions.create({
      model: MODEL,
      messages: messages as OpenAI.Chat.ChatCompletionMessageParam[],
      tools: TOOL_DEFINITIONS,
      tool_choice: 'auto',
    });

    const choice = response.choices[0];
    const assistantMessage = choice.message;

    // Append assistant turn
    messages.push({
      role: 'assistant',
      content: assistantMessage.content ?? '',
      tool_calls: assistantMessage.tool_calls,
    });

    // ── Final answer ──────────────────────────────────────────────────────
    if (choice.finish_reason === 'stop' || !assistantMessage.tool_calls?.length) {
      finalMessage = assistantMessage.content ?? '';
      break;
    }

    // ── Tool calls ────────────────────────────────────────────────────────
    if (choice.finish_reason === 'tool_calls' && assistantMessage.tool_calls) {
      for (const toolCall of assistantMessage.tool_calls) {
        const toolName = toolCall.function.name;
        let toolInput: Record<string, unknown> = {};

        try {
          toolInput = JSON.parse(toolCall.function.arguments) as Record<string, unknown>;
        } catch {
          // malformed arguments — pass empty object
        }

        const result: ToolResult = await dispatchTool(toolName, toolInput);

        const log: ToolCallLog = { toolName, input: toolInput, result };
        toolCallLogs.push(log);
        onToolCall?.(log);

        // Feed result back as a tool message
        messages.push({
          role: 'tool',
          tool_call_id: toolCall.id,
          content: JSON.stringify(result),
        });
      }
    }
  }

  if (iterations >= MAX_ITERATIONS && !finalMessage) {
    finalMessage = "I'm sorry, I ran into an issue processing your request. Please try again.";
  }

  return { message: finalMessage, toolCallLogs };
}

// ── Serialization helpers ────────────────────────────────────────────────────

export function deserializeHistory(json: unknown): ConversationMessage[] {
  if (!Array.isArray(json)) return [];
  return (json as ConversationMessage[]).filter(
    (m) => m.role === 'user' || m.role === 'assistant',
  );
}
