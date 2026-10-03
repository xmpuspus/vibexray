import { z } from 'zod';
import { ToolError, TransientError } from './errors.ts';
import { toolByName, type ToolContext } from './tools.ts';

export interface ToolOutcome {
  ok: boolean;
  output?: unknown;
  error?: string;
  latencyMs: number;
  attempts: number;
}

const DEFAULT_TIMEOUT_MS = 5000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function withTimeout<T>(work: Promise<T>, ms: number, name: string): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new TransientError(`${name} did not answer within ${ms} ms`)), ms);
  });
  return Promise.race([work, timeout]).finally(() => clearTimeout(timer));
}

function log(entry: Record<string, unknown>) {
  if (process.env.VITEST) return;
  console.log(JSON.stringify({ ts: new Date().toISOString(), event: 'tool_call', ...entry }));
}

/**
 * Runs one tool call requested by the model: validates the input, applies a timeout,
 * retries transient failures with backoff, and turns every failure into a message
 * the model can act on instead of an exception that kills the conversation.
 */
export async function executeTool(name: string, input: unknown, ctx: ToolContext): Promise<ToolOutcome> {
  const started = performance.now();
  const finish = (outcome: Omit<ToolOutcome, 'latencyMs'>): ToolOutcome => {
    const result = { ...outcome, latencyMs: Math.round(performance.now() - started) };
    log({ tool: name, ok: result.ok, latencyMs: result.latencyMs, attempts: result.attempts, error: result.error });
    return result;
  };

  const tool = toolByName.get(name);
  if (!tool) {
    return finish({ ok: false, attempts: 0, error: `Unknown tool "${name}". Available tools: ${[...toolByName.keys()].join(', ')}.` });
  }

  const parsed = tool.schema.safeParse(input);
  if (!parsed.success) {
    return finish({ ok: false, attempts: 0, error: `Invalid parameters for ${name}:\n${z.prettifyError(parsed.error)}` });
  }

  const maxAttempts = (tool.retries ?? 0) + 1;
  for (let attempt = 1; ; attempt++) {
    try {
      const output = await withTimeout(
        Promise.resolve().then(() => tool.run(parsed.data, ctx)),
        tool.timeoutMs ?? DEFAULT_TIMEOUT_MS,
        name,
      );
      return finish({ ok: true, output, attempts: attempt });
    } catch (err) {
      if (err instanceof TransientError && attempt < maxAttempts) {
        await sleep(200 * 2 ** (attempt - 1));
        continue;
      }
      if (err instanceof ToolError) return finish({ ok: false, attempts: attempt, error: err.message });
      if (err instanceof TransientError) {
        return finish({ ok: false, attempts: attempt, error: `${err.message}. The system is temporarily unavailable, offer a callback instead.` });
      }
      console.error(`[${name}] unexpected failure`, err);
      return finish({ ok: false, attempts: attempt, error: 'Internal error in this tool. Apologise and offer a callback with a human agent.' });
    }
  }
}
