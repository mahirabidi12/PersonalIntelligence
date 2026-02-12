import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Search, MoreVertical, Smile, Paperclip, Mic, Send } from 'lucide-react';

const DEFAULT_AVATAR = '/img/icons8-account-96.png';

function formatMsgTime(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDateSeparator(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  const dayMs = 86400000;

  if (diff < dayMs && date.getDate() === now.getDate()) return 'TODAY';
  if (diff < 2 * dayMs) return 'YESTERDAY';
  return date.toLocaleDateString([], { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function shouldShowDateSep(messages, idx) {
  if (idx === 0) return true;
  const curr = new Date(messages[idx].created_at).toDateString();
  const prev = new Date(messages[idx - 1].created_at).toDateString();
  return curr !== prev;
}

function shouldShowTail(messages, idx) {
  if (idx === 0) return true;
  return messages[idx].sender_id !== messages[idx - 1].sender_id ||
    shouldShowDateSep(messages, idx);
}

function DoubleCheck({ read }) {
  return (
    <span className={`wa-msg-check ${read ? 'read' : 'sent'}`}>
      <svg viewBox="0 0 16 15" fill="currentColor">
        <path d="M15.01 3.316l-.478-.372a.365.365 0 0 0-.51.063L8.666 9.88a.32.32 0 0 1-.484.032l-.358-.325a.32.32 0 0 0-.484.032l-.378.48a.418.418 0 0 0 .036.54l1.32 1.267a.32.32 0 0 0 .484-.034l6.272-8.048a.366.366 0 0 0-.064-.512zm-4.1 0l-.478-.372a.365.365 0 0 0-.51.063L4.566 9.88a.32.32 0 0 1-.484.032L1.892 7.77a.366.366 0 0 0-.516.005l-.423.433a.364.364 0 0 0 .006.514l3.255 3.185a.32.32 0 0 0 .484-.033l6.272-8.048a.365.365 0 0 0-.063-.51z" />
      </svg>
    </span>
  );
}

export default function ChatPanel({
  conversation,
  messages,
  currentUser,
  onSendMessage,
  typingUsers,
  sendTyping,
  sendStopTyping,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const typingTimeout = useRef(null);

  const other = conversation?.participants?.[0];
  const name = conversation?.is_group ? conversation.group_name : other?.username || 'Unknown';
  const avatar = conversation?.is_group ? DEFAULT_AVATAR : other?.avatar || DEFAULT_AVATAR;
  const isOnline = other?.is_online;
  const isTyping = typingUsers[conversation?.conversation_id];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input);
    setInput('');
    if (typingTimeout.current) {
      clearTimeout(typingTimeout.current);
      sendStopTyping(conversation.conversation_id);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);

    // Typing indicator
    sendTyping(conversation.conversation_id);
    if (typingTimeout.current) clearTimeout(typingTimeout.current);
    typingTimeout.current = setTimeout(() => {
      sendStopTyping(conversation.conversation_id);
    }, 2000);
  };

  let statusText = 'click here for contact info';
  if (isTyping) {
    statusText = 'typing...';
  } else if (isOnline) {
    statusText = 'online';
  }

  return (
    <div className="wa-chat-panel" data-testid="chat-panel">
      {/* Header */}
      <div className="wa-chat-header" data-testid="chat-header">
        <div className="wa-chat-header-left">
          <img
            className="wa-contact-avatar"
            src={avatar}
            alt={name}
            onError={(e) => { e.target.src = DEFAULT_AVATAR; }}
          />
          <div className="wa-chat-header-info">
            <h4 data-testid="chat-contact-name">{name}</h4>
            <p className={isTyping ? 'wa-typing-indicator' : ''} data-testid="chat-status">
              {statusText}
            </p>
          </div>
        </div>
        <div className="wa-chat-header-actions">
          <button className="wa-icon-btn" data-testid="chat-search-btn">
            <Search size={20} />
          </button>
          <button className="wa-icon-btn" data-testid="chat-menu-btn">
            <MoreVertical size={20} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="wa-messages-area" data-testid="messages-area" style={{
        backgroundImage: `url(${process.env.PUBLIC_URL}/img/bg-chat-tile-dark_a4be512e7195b6b733d9110b408f075d.png)`,
        backgroundRepeat: 'repeat',
      }}>
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(239,234,226,0.92)', pointerEvents: 'none', zIndex: 0 }} />
        {messages.map((msg, idx) => {
          const isSent = msg.sender_id === currentUser?.user_id;
          const showTail = shouldShowTail(messages, idx);
          const showDate = shouldShowDateSep(messages, idx);
          const isRead = msg.read_by?.length > 1;

          return (
            <React.Fragment key={msg.message_id}>
              {showDate && (
                <div className="wa-date-separator">
                  <span>{formatDateSeparator(msg.created_at)}</span>
                </div>
              )}
              <div className={`wa-msg-row ${isSent ? 'sent' : 'received'}`} data-testid={`message-${msg.message_id}`}>
                <div className={`wa-msg-bubble ${isSent ? 'sent' : 'received'}`}>
                  {showTail && <div className="wa-msg-tail" />}
                  <span className="wa-msg-content">{msg.content}</span>
                  <span className="wa-msg-meta">
                    <span className="wa-msg-time">{formatMsgTime(msg.created_at)}</span>
                    {isSent && <DoubleCheck read={isRead} />}
                  </span>
                </div>
              </div>
            </React.Fragment>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="wa-input-area" data-testid="message-input-area">
        <button className="wa-icon-btn" data-testid="emoji-btn">
          <Smile size={24} />
        </button>
        <button className="wa-icon-btn" data-testid="attach-btn">
          <Paperclip size={24} />
        </button>
        <input
          className="wa-message-input"
          type="text"
          placeholder="Type a message"
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          data-testid="message-input"
        />
        {input.trim() ? (
          <button className="wa-icon-btn" onClick={handleSend} data-testid="send-btn">
            <Send size={24} />
          </button>
        ) : (
          <button className="wa-icon-btn" data-testid="mic-btn">
            <Mic size={24} />
          </button>
        )}
      </div>
    </div>
  );
}
