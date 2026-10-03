import { randomUUID } from 'node:crypto';
import type Anthropic from '@anthropic-ai/sdk';
import { executeTool } from './executor.ts';
import { systemPrompt } from './prompt.ts';
import { anthropicTools, type ToolContext } from './tools.ts';

export type TraceEvent =
  | { type: 'model_call'; step: number; model: string }
  | { type: 'thinking'; text: string }
  | { type: 'tool_call'; id: string; name: string; input: unknown }
  | { type: 'tool_result'; id: string; name: string; ok: boolean; output?: unknown; error?: string; latencyMs: number; attempts: number }
  | { type: 'confirmation_required'; actionId: string; tool: string; summary: string }
  | { type: 'assistant_text'; text: string }
  | { type: 'usage'; inputTokens: number; outputTokens: number; costUsd: number; totalCostUsd: number }
  | { type: 'done'; stopReason: string }
  | { type: 'error'; message: string };

export type Emit = (event: TraceEvent) => void;

/** The only part of the Anthropic client the agent needs, which keeps it easy to fake in tests. */
export interface MessagesClient {
  messages: { create(params: Anthropic.MessageCreateParamsNonStreaming): Promise<Anthropic.Message> };
}

export interface AgentOptions {
  model: string;
  maxTokens: number;
  maxSteps: number;
  priceInPerMTok: number;
  priceOutPerMTok: number;
  today: string;
}

interface PendingAction {
  tool: string;
  summary: string;
  execute: () => unknown;
}

export class Session {
  messages: Anthropic.MessageParam[] = [];
  pending = new Map<string, PendingAction>();
  totalCostUsd = 0;
  busy = false;
}

export class SupportAgent {
  private readonly tools = anthropicTools();

  constructor(
    private readonly client: MessagesClient,
    private readonly opts: AgentOptions,
  ) {}

  async send(session: Session, text: string, emit: Emit) {
    session.messages.push({ role: 'user', content: text });
    await this.loop(session, emit);
  }

  /** Called when the customer presses Approve or Decline on a parked action. */
  async resolve(session: Session, actionId: string, approve: boolean, emit: Emit) {
    const action = session.pending.get(actionId);
    if (!action) {
      emit({ type: 'error', message: 'This action has expired or was already handled.' });
      emit({ type: 'done', stopReason: 'error' });
      return;
    }
    session.pending.delete(actionId);

    let note = `The customer declined action ${actionId} (${action.summary}). Nothing was changed.`;
    if (approve) {
      const started = performance.now();
      try {
        const output = await action.execute();
        emit({ type: 'tool_result', id: actionId, name: action.tool, ok: true, output, latencyMs: Math.round(performance.now() - started), attempts: 1 });
        note = `The customer approved action ${actionId} (${action.summary}) and it was executed. Result: ${JSON.stringify(output)}`;
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        emit({ type: 'tool_result', id: actionId, name: action.tool, ok: false, error: message, latencyMs: Math.round(performance.now() - started), attempts: 1 });
        note = `The customer approved action ${actionId}, but it failed: ${message}`;
      }
    }
    session.messages.push({ role: 'user', content: `[System note, not written by the customer] ${note}` });
    await this.loop(session, emit);
  }

  private async loop(session: Session, emit: Emit) {
    const ctx: ToolContext = {
      requestConfirmation: (tool, summary, execute) => {
        const actionId = `act_${randomUUID().slice(0, 8)}`;
        session.pending.set(actionId, { tool, summary, execute });
        emit({ type: 'confirmation_required', actionId, tool, summary });
        return { actionId };
      },
    };

    for (let step = 1; step <= this.opts.maxSteps; step++) {
      emit({ type: 'model_call', step, model: this.opts.model });
      const response = await this.client.messages.create({
        model: this.opts.model,
        max_tokens: this.opts.maxTokens,
        system: systemPrompt(this.opts.today),
        tools: this.tools,
        messages: session.messages,
      });
      this.trackUsage(session, response.usage, emit);

      // The assistant turn goes back verbatim: tool_use ids and thinking blocks must round-trip.
      session.messages.push({ role: 'assistant', content: response.content as Anthropic.ContentBlockParam[] });

      const results: Anthropic.ToolResultBlockParam[] = [];
      for (const block of response.content) {
        if (block.type === 'thinking' && block.thinking.trim()) {
          emit({ type: 'thinking', text: block.thinking.trim() });
        } else if (block.type === 'text' && block.text.trim()) {
          emit({ type: 'assistant_text', text: block.text.trim() });
        } else if (block.type === 'tool_use') {
          emit({ type: 'tool_call', id: block.id, name: block.name, input: block.input });
          const outcome = await executeTool(block.name, block.input, ctx);
          emit({ type: 'tool_result', id: block.id, name: block.name, ...outcome });
          results.push({
            type: 'tool_result',
            tool_use_id: block.id,
            content: JSON.stringify(outcome.ok ? outcome.output : { error: outcome.error }),
            is_error: !outcome.ok,
          });
        }
      }

      if (results.length === 0) {
        emit({ type: 'done', stopReason: response.stop_reason ?? 'end_turn' });
        return;
      }
      session.messages.push({ role: 'user', content: results });
    }

    const text = 'Sorry, this request needs more steps than I am allowed to take. A human agent will follow up by email.';
    session.messages.push({ role: 'assistant', content: text });
    emit({ type: 'assistant_text', text });
    emit({ type: 'done', stopReason: 'max_steps' });
  }

  private trackUsage(session: Session, usage: Anthropic.Usage, emit: Emit) {
    const inputTokens = usage.input_tokens ?? 0;
    const outputTokens = usage.output_tokens ?? 0;
    const costUsd = (inputTokens * this.opts.priceInPerMTok + outputTokens * this.opts.priceOutPerMTok) / 1_000_000;
    session.totalCostUsd += costUsd;
    emit({ type: 'usage', inputTokens, outputTokens, costUsd, totalCostUsd: session.totalCostUsd });
  }
}
