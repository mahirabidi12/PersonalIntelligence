import React from 'react';
import { Lock } from 'lucide-react';

export default function EmptyChat() {
  return (
    <div className="wa-empty-chat" data-testid="empty-chat">
      <img
        className="wa-empty-chat-icon"
        src="/img/icons8-whatsapp-48.png"
        alt="WhatsApp2"
        style={{ width: 200, opacity: 0.08 }}
      />
      <h2 className="wa-empty-title">WhatsApp2 Web</h2>
      <p className="wa-empty-desc">
        Send and receive messages without keeping your phone online.<br />
        Use WhatsApp on up to 4 linked devices and 1 phone at the same time.
      </p>
      <div className="wa-empty-divider" />
      <p className="wa-empty-encrypt">
        <Lock size={14} />
        End-to-end encrypted
      </p>
    </div>
  );
}
