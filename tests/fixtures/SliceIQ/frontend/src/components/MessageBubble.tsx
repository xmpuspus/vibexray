import { ChatMessage } from '../types';
import ToolCallLogPanel from './ToolCallLog';

interface MessageBubbleProps {
  message: ChatMessage;
  customerName?: string;
}

// Very basic markdown-to-HTML: bold **text** and line breaks
function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>');
}

export default function MessageBubble({ message, customerName }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const formattedTime = new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(message.timestamp);

  return (
    <div
      className={`flex items-end gap-2.5 animate-fade-in ${
        isUser ? 'flex-row-reverse' : 'flex-row'
      }`}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-brand-500 flex items-center justify-center text-white text-sm flex-shrink-0 mb-1">
          🍕
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Sender label */}
        <span className="text-[11px] text-gray-400 mb-1 px-1">
          {isUser ? (customerName ?? 'You') : 'SliceIQ'} · {formattedTime}
        </span>

        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isUser
              ? 'bg-brand-500 text-white rounded-br-sm'
              : message.isError
              ? 'bg-red-50 text-red-700 border border-red-200 rounded-bl-sm'
              : 'bg-white text-gray-800 border border-gray-200 rounded-bl-sm'
          }`}
        >
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <p
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />
          )}
        </div>

        {/* Tool call log (agent messages only) */}
        {!isUser && message.toolCallLogs && message.toolCallLogs.length > 0 && (
          <div className="mt-1 px-1 w-full">
            <ToolCallLogPanel logs={message.toolCallLogs} />
          </div>
        )}
      </div>
    </div>
  );
}
