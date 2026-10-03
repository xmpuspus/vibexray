const $ = (sel) => document.querySelector(sel);

const newId = () =>
  crypto.randomUUID ? crypto.randomUUID() : `session-${Math.random().toString(36).slice(2)}`;

function loadSessionId() {
  try {
    const saved = sessionStorage.getItem('northwind_session_id');
    if (saved) return saved;
    const id = newId();
    sessionStorage.setItem('northwind_session_id', id);
    return id;
  } catch {
    return newId();
  }
}

function saveSessionId(id) {
  try {
    sessionStorage.setItem('northwind_session_id', id);
  } catch {
    // Storage unavailable: the in-memory id is enough.
  }
}

const state = {
  sessionId: loadSessionId(),
  model: null,
  turnCount: 0,
  tokensIn: 0,
  tokensOut: 0,
  cost: 0,
  streaming: false,
  abortController: null,
  toolCards: new Map(),
  typingBubble: null,
};

const els = {
  modelBadge: $('#model-badge'),
  tokensIn: $('#tokens-in'),
  tokensOut: $('#tokens-out'),
  cost: $('#cost'),
  resetBtn: $('#reset-btn'),
  chatList: $('#chat-list'),
  emptyState: $('#empty-state'),
  textarea: $('#message-input'),
  sendBtn: $('#send-btn'),
  traceList: $('#trace-list'),
};

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function toJson(value) {
  try {
    return JSON.stringify(value, null, 2) ?? String(value);
  } catch {
    return String(value);
  }
}

async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    if (!res.ok) throw new Error('config unavailable');
    const config = await res.json();
    state.model = config.model;
    els.modelBadge.textContent = config.model;
    els.modelBadge.title = `endpoint: ${config.endpoint}`;
  } catch {
    els.modelBadge.textContent = 'model unavailable';
  }
}

function updateHeader() {
  els.tokensIn.textContent = state.tokensIn.toLocaleString('en-US');
  els.tokensOut.textContent = state.tokensOut.toLocaleString('en-US');
  els.cost.textContent = state.cost.toFixed(4);
}

// ---------- Chat ----------

const scrollChat = () => { els.chatList.scrollTop = els.chatList.scrollHeight; };
const scrollTrace = () => { els.traceList.scrollTop = els.traceList.scrollHeight; };

function appendChat(node) {
  els.emptyState.style.display = 'none';
  // Keep the typing indicator as the last bubble.
  if (state.typingBubble) els.chatList.insertBefore(node, state.typingBubble);
  else els.chatList.appendChild(node);
  scrollChat();
}

function bubble(role, html) {
  const wrapper = document.createElement('div');
  wrapper.className = `msg ${role}`;
  const inner = document.createElement('div');
  inner.className = 'bubble';
  inner.innerHTML = html;
  wrapper.appendChild(inner);
  return wrapper;
}

function renderAssistantText(text) {
  const lines = escapeHtml(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .split('\n');
  let html = '';
  for (let i = 0; i < lines.length; ) {
    const line = lines[i].trim();
    if (line.startsWith('- ')) {
      html += '<ul>';
      while (i < lines.length && lines[i].trim().startsWith('- ')) {
        html += `<li>${lines[i].trim().slice(2)}</li>`;
        i += 1;
      }
      html += '</ul>';
    } else {
      if (line) html += `<p>${line}</p>`;
      i += 1;
    }
  }
  return html;
}

function showTyping() {
  if (state.typingBubble) return;
  state.typingBubble = bubble('assistant', '<span class="typing"><span></span><span></span><span></span></span>');
  els.chatList.appendChild(state.typingBubble);
  scrollChat();
}

function removeTyping() {
  state.typingBubble?.remove();
  state.typingBubble = null;
}

function addChatError(message) {
  const div = document.createElement('div');
  div.className = 'chat-error';
  div.textContent = message;
  appendChat(div);
}

function addConfirmationCard(actionId, tool, summary) {
  const card = document.createElement('div');
  card.className = 'confirm-card';
  card.innerHTML = `
    <div class="confirm-title">Approval needed</div>
    <div class="confirm-summary">${escapeHtml(summary)}</div>
    <div class="confirm-tool">${escapeHtml(tool)}</div>
    <div class="confirm-actions">
      <button class="btn approve-btn" type="button">Approve</button>
      <button class="btn decline-btn" type="button">Decline</button>
    </div>
    <div class="confirm-status" role="status"></div>`;
  appendChat(card);

  const approveBtn = card.querySelector('.approve-btn');
  const declineBtn = card.querySelector('.decline-btn');
  const status = card.querySelector('.confirm-status');

  const decide = (approve) => {
    if (state.streaming || approveBtn.disabled) return;
    approveBtn.disabled = true;
    declineBtn.disabled = true;
    status.textContent = approve ? 'Approved' : 'Declined';
    startStream({ actionId, approve, label: approve ? 'Approved action' : 'Declined action' });
  };
  approveBtn.addEventListener('click', () => decide(true));
  declineBtn.addEventListener('click', () => decide(false));
}

// ---------- Trace ----------

function traceRow(className, text) {
  const row = document.createElement('div');
  row.className = `trace-row ${className}`;
  row.textContent = text;
  els.traceList.appendChild(row);
  scrollTrace();
  return row;
}

function addThinking(text) {
  const row = traceRow('thinking', '');
  const span = document.createElement('span');
  span.className = 'thinking-text';
  const short = text.length > 120 ? `${text.replace(/\s+/g, ' ').slice(0, 120)}…` : text;
  span.textContent = short;
  row.appendChild(span);
  if (short !== text) {
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'link-btn';
    toggle.textContent = 'show';
    toggle.addEventListener('click', () => {
      const expand = toggle.textContent === 'show';
      span.textContent = expand ? text : short;
      toggle.textContent = expand ? 'hide' : 'show';
    });
    row.appendChild(toggle);
  }
}

function createToolCard(id, name) {
  const card = document.createElement('div');
  card.className = 'trace-card tool-card';
  card.innerHTML = `
    <div class="tool-head">
      <span class="tool-name">${escapeHtml(name)}</span>
      <span class="tool-badge running">running…</span>
    </div>
    <div class="tool-result-area"></div>`;
  els.traceList.appendChild(card);
  state.toolCards.set(id, card);
  scrollTrace();
  return card;
}

function addToolCall(id, name, input) {
  const card = createToolCard(id, name);
  const pre = document.createElement('pre');
  pre.className = 'trace-json';
  pre.textContent = toJson(input);
  card.insertBefore(pre, card.querySelector('.tool-result-area'));
}

function updateToolResult({ id, name, ok, output, error, latencyMs = 0, attempts = 1 }) {
  const card = state.toolCards.get(id) ?? createToolCard(id, name);
  const badge = card.querySelector('.tool-badge');
  badge.textContent = ok ? 'OK' : 'ERROR';
  badge.className = `tool-badge ${ok ? 'ok' : 'err'}`;

  const area = card.querySelector('.tool-result-area');
  area.innerHTML = '';
  const meta = document.createElement('div');
  meta.className = 'tool-meta';
  meta.innerHTML = `<span class="tool-latency">${Number(latencyMs)} ms</span>`;
  if (attempts > 1) {
    meta.insertAdjacentHTML('beforeend', `<span class="tool-badge warn">${Number(attempts)} attempts (retried)</span>`);
  }
  area.appendChild(meta);

  if (!ok) {
    const err = document.createElement('div');
    err.className = 'tool-error';
    err.textContent = error ?? 'Tool failed';
    area.appendChild(err);
  } else if (output !== undefined) {
    const json = toJson(output);
    const pre = document.createElement('pre');
    pre.className = 'trace-json';
    pre.textContent = json;
    if (json.length > 280) {
      pre.classList.add('collapsed');
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'link-btn';
      toggle.textContent = 'show result';
      toggle.addEventListener('click', () => {
        const collapsed = pre.classList.toggle('collapsed');
        toggle.textContent = collapsed ? 'show result' : 'hide result';
      });
      area.appendChild(toggle);
    }
    area.appendChild(pre);
  }
  scrollTrace();
}

// ---------- Streaming ----------

function setInputEnabled(enabled) {
  els.textarea.disabled = !enabled;
  els.sendBtn.disabled = !enabled;
  document.querySelectorAll('.suggestion-chip').forEach((chip) => { chip.disabled = !enabled; });
  if (enabled) els.textarea.focus();
}

function handleEvent(evt) {
  switch (evt.type) {
    case 'model_call':
      traceRow('model-call', `LLM call #${evt.step} · ${evt.model}`);
      break;
    case 'thinking':
      if (evt.text) addThinking(evt.text);
      break;
    case 'tool_call':
      addToolCall(evt.id, evt.name, evt.input);
      break;
    case 'tool_result':
      updateToolResult(evt);
      break;
    case 'confirmation_required':
      addConfirmationCard(evt.actionId, evt.tool, evt.summary);
      traceRow('confirmation-required', `Waiting for customer approval · ${evt.summary}`);
      break;
    case 'assistant_text':
      removeTyping();
      appendChat(bubble('assistant', renderAssistantText(evt.text ?? '')));
      break;
    case 'usage':
      state.tokensIn += evt.inputTokens ?? 0;
      state.tokensOut += evt.outputTokens ?? 0;
      if (typeof evt.totalCostUsd === 'number') state.cost = evt.totalCostUsd;
      updateHeader();
      break;
    case 'done':
      traceRow('done', `stop: ${evt.stopReason}`);
      break;
    case 'error':
      addChatError(evt.message ?? 'Agent error');
      traceRow('error', evt.message ?? 'Agent error');
      break;
    default:
      break;
  }
}

function parseBlock(block) {
  let data = '';
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('data:')) data += line.slice(5).trim();
  }
  if (!data) return;
  try {
    handleEvent(JSON.parse(data));
  } catch {
    // Ignore a malformed block rather than breaking the stream.
  }
}

async function startStream({ message, actionId, approve, label }) {
  if (state.streaming) return;
  state.streaming = true;
  setInputEnabled(false);
  showTyping();

  state.turnCount += 1;
  const title = label ?? (message.length > 40 ? `${message.slice(0, 40)}…` : message);
  traceRow('turn-divider', `Turn ${state.turnCount} — ${title}`);

  const controller = new AbortController();
  state.abortController = controller;
  const endpoint = actionId ? '/api/confirm' : '/api/chat';
  const body = actionId
    ? { sessionId: state.sessionId, actionId, approve }
    : { sessionId: state.sessionId, message };

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) {
      let reason = `HTTP ${res.status}`;
      try {
        reason = (await res.json()).error ?? reason;
      } catch {
        // Body was not JSON.
      }
      throw new Error(reason);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let match;
      while ((match = /\r?\n\r?\n/.exec(buffer)) !== null) {
        parseBlock(buffer.slice(0, match.index));
        buffer = buffer.slice(match.index + match[0].length);
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) parseBlock(buffer);
  } catch (err) {
    if (err.name !== 'AbortError') {
      addChatError(err.message || 'Network error');
      traceRow('error', err.message || 'Network error');
    }
  } finally {
    removeTyping();
    state.streaming = false;
    state.abortController = null;
    setInputEnabled(true);
  }
}

// ---------- Input and reset ----------

function autoGrow() {
  els.textarea.style.height = 'auto';
  els.textarea.style.height = `${Math.min(els.textarea.scrollHeight, 120)}px`;
}

function send(text) {
  const message = (text ?? '').trim();
  if (!message || state.streaming) return;
  appendChat(bubble('user', escapeHtml(message)));
  els.textarea.value = '';
  autoGrow();
  startStream({ message });
}

async function reset() {
  state.abortController?.abort();
  try {
    await fetch('/api/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId: state.sessionId }),
    });
  } catch {
    // The local reset still goes ahead.
  }
  state.sessionId = newId();
  saveSessionId(state.sessionId);
  Object.assign(state, { turnCount: 0, tokensIn: 0, tokensOut: 0, cost: 0, streaming: false, abortController: null });
  state.toolCards.clear();
  removeTyping();
  updateHeader();
  els.chatList.querySelectorAll('.msg, .chat-error, .confirm-card').forEach((el) => el.remove());
  els.traceList.innerHTML = '';
  els.emptyState.style.display = '';
  els.textarea.value = '';
  autoGrow();
  setInputEnabled(true);
}

els.textarea.addEventListener('input', autoGrow);
els.textarea.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    send(els.textarea.value);
  }
});
els.sendBtn.addEventListener('click', () => send(els.textarea.value));
document.querySelectorAll('.suggestion-chip').forEach((chip) => {
  chip.addEventListener('click', () => send(chip.textContent));
});
els.resetBtn.addEventListener('click', reset);

updateHeader();
loadConfig();
