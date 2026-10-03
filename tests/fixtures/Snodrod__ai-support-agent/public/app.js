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
