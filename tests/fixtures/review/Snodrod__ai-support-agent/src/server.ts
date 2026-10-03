import { fileURLToPath } from 'node:url';
import Anthropic from '@anthropic-ai/sdk';
import express, { type Response } from 'express';
import { SupportAgent, Session, type Emit } from './agent.ts';
import { config } from './config.ts';

if (!config.apiKey) {
  console.warn('ANTHROPIC_API_KEY is not set: model calls will fail. Copy .env.example to .env and fill it in.');
}

const client = new Anthropic({ apiKey: config.apiKey, baseURL: config.baseURL });
const agent = new SupportAgent(client, config);

// In-memory sessions are enough for a demo; production would use Redis or a database.
const sessions = new Map<string, Session>();
const validId = (id: unknown): id is string => typeof id === 'string' && /^[\w-]{8,64}$/.test(id);

function session(id: string) {
  let s = sessions.get(id);
  if (!s) {
    s = new Session();
    sessions.set(id, s);
  }
  return s;
}

function describe(err: unknown) {
  if (err instanceof Anthropic.APIError) return `Model API error ${err.status ?? ''}: ${err.message}`.trim();
  return err instanceof Error ? err.message : String(err);
}

/** Streams agent events to the browser as Server-Sent Events. */
async function stream(res: Response, s: Session, work: (emit: Emit) => Promise<void>) {
  if (s.busy) {
    res.status(409).json({ error: 'The agent is still answering the previous message.' });
    return;
  }
  s.busy = true;
  res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
  const emit: Emit = (event) => res.write(`event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`);
  try {
    await work(emit);
  } catch (err) {
    console.error(err);
    emit({ type: 'error', message: describe(err) });
    emit({ type: 'done', stopReason: 'error' });
  } finally {
    s.busy = false;
    res.end();
  }
}

const app = express();
app.use(express.json({ limit: '32kb' }));
app.use(express.static(fileURLToPath(new URL('../public', import.meta.url))));

app.get('/api/config', (_req, res) => {
  res.json({ model: config.model, endpoint: config.baseURL ? 'custom' : 'anthropic' });
});

app.post('/api/chat', async (req, res) => {
  const { sessionId, message } = req.body ?? {};
  if (!validId(sessionId)) return void res.status(400).json({ error: 'Invalid sessionId.' });
  if (typeof message !== 'string' || !message.trim() || message.length > 2000) {
    return void res.status(400).json({ error: 'The message must be 1-2000 characters.' });
  }
  const s = session(sessionId);
  await stream(res, s, (emit) => agent.send(s, message.trim(), emit));
});

app.post('/api/confirm', async (req, res) => {
  const { sessionId, actionId, approve } = req.body ?? {};
  if (!validId(sessionId) || typeof actionId !== 'string' || typeof approve !== 'boolean') {
    return void res.status(400).json({ error: 'Expected sessionId, actionId and approve.' });
  }
  const s = session(sessionId);
  await stream(res, s, (emit) => agent.resolve(s, actionId, approve, emit));
});

app.post('/api/reset', (req, res) => {
  const { sessionId } = req.body ?? {};
  if (validId(sessionId)) sessions.delete(sessionId);
  res.json({ ok: true });
});

app.listen(config.port, () => {
  console.log(`Support agent running on http://localhost:${config.port} (model: ${config.model})`);
});
