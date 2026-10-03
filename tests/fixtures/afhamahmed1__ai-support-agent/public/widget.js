/*
 * Embeddable AI Support Agent, vanilla JS widget (no dependencies).
 * Streams answers token-by-token (SSE) and falls back to plain JSON
 * if streaming is unavailable.
 * Usage:
 *   <script src="https://your-host/widget.js"
 *           data-api-url="https://your-host"
 *           data-title="Ask AI"></script>
 */
(function () {
  var script = document.currentScript;
  var API = (script && script.getAttribute('data-api-url')) || '';
  var TITLE = (script && script.getAttribute('data-title')) || 'Ask AI';
  var history = [];

  var css = [
    '.aisa-btn{position:fixed;right:22px;bottom:22px;width:58px;height:58px;border-radius:50%;border:none;cursor:pointer;background:linear-gradient(135deg,#4f46e5,#06b6d4);color:#fff;font-size:24px;box-shadow:0 10px 30px rgba(79,70,229,.45);z-index:99998}',
    '.aisa-panel{position:fixed;right:22px;bottom:92px;width:360px;max-width:calc(100vw - 44px);height:520px;max-height:calc(100vh - 120px);background:#fff;border-radius:16px;box-shadow:0 24px 60px rgba(15,23,42,.28);display:none;flex-direction:column;overflow:hidden;z-index:99999;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}',
    '.aisa-panel.open{display:flex}',
    '.aisa-head{background:linear-gradient(135deg,#4f46e5,#06b6d4);color:#fff;padding:16px 18px;font-weight:600}',
    '.aisa-msgs{flex:1;overflow-y:auto;padding:16px;background:#f8fafc}',
    '.aisa-msg{margin-bottom:12px;display:flex}',
    '.aisa-msg .b{padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.45;max-width:82%;white-space:pre-wrap}',
    '.aisa-msg.user{justify-content:flex-end}',
    '.aisa-msg.user .b{background:#4f46e5;color:#fff;border-bottom-right-radius:4px}',
    '.aisa-msg.bot .b{background:#fff;color:#0f172a;border:1px solid #e2e8f0;border-bottom-left-radius:4px}',
    '.aisa-foot{display:flex;gap:8px;padding:12px;border-top:1px solid #e2e8f0;background:#fff}',
    '.aisa-foot input{flex:1;border:1px solid #cbd5e1;border-radius:10px;padding:10px 12px;font-size:14px;outline:none}',
    '.aisa-foot button{border:none;background:#4f46e5;color:#fff;border-radius:10px;padding:0 16px;cursor:pointer;font-weight:600}',
    '.aisa-typing{font-size:13px;color:#94a3b8;padding:0 16px 10px;display:none}'
  ].join('');
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var btn = document.createElement('button');
  btn.className = 'aisa-btn';
  btn.setAttribute('aria-label', 'Open chat');
  btn.innerHTML = '&#128172;';

  var panel = document.createElement('div');
  panel.className = 'aisa-panel';
  panel.innerHTML =
    '<div class="aisa-head">' + TITLE + '</div>' +
    '<div class="aisa-msgs" id="aisa-msgs"></div>' +
    '<div class="aisa-typing" id="aisa-typing">Assistant is typing...</div>' +
    '<form class="aisa-foot" id="aisa-form">' +
      '<input id="aisa-input" placeholder="Type your question..." autocomplete="off" />' +
      '<button type="submit">Send</button>' +
    '</form>';

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var msgs = panel.querySelector('#aisa-msgs');
  var typing = panel.querySelector('#aisa-typing');

  function add(role, text) {
    var row = document.createElement('div');
    row.className = 'aisa-msg ' + role;
    var bubble = document.createElement('div');
    bubble.className = 'b';
    bubble.textContent = text;
    row.appendChild(bubble);
    msgs.appendChild(row);
    msgs.scrollTop = msgs.scrollHeight;
    return bubble;
  }

  function remember(q, answer) {
    history.push({ role: 'user', content: q });
    history.push({ role: 'assistant', content: answer });
    if (history.length > 12) history = history.slice(-12);
  }

  /* Plain JSON fallback (also the path for very old browsers). */
  function askJson(q) {
    return fetch(API + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: q, history: history })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) { return (data && data.answer) || 'Sorry, something went wrong.'; });
  }

  /* Streaming path: POST to the SSE endpoint, append tokens as they arrive.
     Calls onToken(token) per token and resolves with the final answer. */
  function askStream(q, onToken) {
    return fetch(API + '/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: q, history: history })
    }).then(function (res) {
      if (!res.ok || !res.body) throw new Error('stream unavailable');
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';
      var answer = '';

      function pump() {
        return reader.read().then(function (step) {
          if (step.done) return answer;
          buffer += decoder.decode(step.value, { stream: true });
          var parts = buffer.split('\n\n');
          buffer = parts.pop();
          for (var i = 0; i < parts.length; i++) {
            var line = parts[i];
            if (line.indexOf('data: ') !== 0) continue;
            var event;
            try { event = JSON.parse(line.slice(6)); } catch (e) { continue; }
            if (event.type === 'token') {
              answer += event.token;
              onToken(event.token);
            } else if (event.type === 'done') {
              answer = event.answer || answer;
            } else if (event.type === 'error' && !answer) {
              throw new Error(event.message || 'agent error');
            }
          }
          return pump();
        });
      }
      return pump();
    });
  }

  add('bot', 'Hi! Ask me anything about the product.');
  btn.addEventListener('click', function () { panel.classList.toggle('open'); });

  panel.querySelector('#aisa-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var input = panel.querySelector('#aisa-input');
    var q = input.value.trim();
    if (!q) return;
    add('user', q);
    input.value = '';
    typing.style.display = 'block';

    var bubble = null;
    var streamed = '';

    askStream(q, function (token) {
      if (!bubble) {
        typing.style.display = 'none';
        bubble = add('bot', '');
      }
      streamed += token;
      bubble.textContent = streamed;
      msgs.scrollTop = msgs.scrollHeight;
    })
      .then(function (answer) {
        typing.style.display = 'none';
        if (bubble) bubble.textContent = answer || streamed;
        else add('bot', answer || 'Sorry, something went wrong.');
        remember(q, answer || streamed);
      })
      .catch(function () {
        // Streaming failed before any token arrived: retry once without it.
        if (bubble) {
          typing.style.display = 'none';
          remember(q, streamed);
          return;
        }
        askJson(q)
          .then(function (answer) {
            typing.style.display = 'none';
            add('bot', answer);
            remember(q, answer);
          })
          .catch(function () {
            typing.style.display = 'none';
            add('bot', 'Network error, is the API running?');
          });
      });
  });
})();
