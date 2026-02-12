import React, { useState } from 'react';
import { Search, MessageSquarePlus, MoreVertical, Filter, ArrowLeft } from 'lucide-react';

const DEFAULT_AVATAR = '/img/icons8-account-96.png';

function formatTime(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  const dayMs = 86400000;

  if (diff < dayMs && date.getDate() === now.getDate()) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  if (diff < 2 * dayMs) return 'Yesterday';
  if (diff < 7 * dayMs) {
    return date.toLocaleDateString([], { weekday: 'long' });
  }
  return date.toLocaleDateString([], { month: '2-digit', day: '2-digit' });
}

export default function Sidebar({
  conversations,
  selectedConv,
  onSelectConv,
  currentUser,
  onLogout,
  users,
  onStartChat,
  searchQuery,
  onSearchChange,
  typingUsers,
}) {
  const [showNewChat, setShowNewChat] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [newChatSearch, setNewChatSearch] = useState('');

  const filteredConvs = conversations.filter((conv) => {
    if (!searchQuery) return true;
    const name = conv.is_group
      ? conv.group_name
      : conv.participants?.[0]?.username;
    return name?.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const filteredUsers = users.filter((u) =>
    u.username.toLowerCase().includes(newChatSearch.toLowerCase())
  );

  const handleNewChatSelect = (userId) => {
    onStartChat(userId);
    setShowNewChat(false);
    setNewChatSearch('');
  };

  return (
    <div className="wa-sidebar" data-testid="sidebar">
      {/* New Chat Panel */}
      {showNewChat && (
        <div className="wa-new-chat-overlay" data-testid="new-chat-panel">
          <div className="wa-new-chat-header">
            <button
              className="wa-icon-btn"
              onClick={() => setShowNewChat(false)}
              data-testid="new-chat-back-btn"
            >
              <ArrowLeft size={20} />
            </button>
            <h3>New chat</h3>
          </div>
          <div className="wa-new-chat-search">
            <div className="wa-search-bar">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search contacts"
                value={newChatSearch}
                onChange={(e) => setNewChatSearch(e.target.value)}
                data-testid="new-chat-search-input"
              />
            </div>
          </div>
          <div className="wa-new-chat-list">
            {filteredUsers.map((user) => (
              <div
                key={user.user_id}
                className="wa-new-chat-user"
                onClick={() => handleNewChatSelect(user.user_id)}
                data-testid={`new-chat-user-${user.user_id}`}
              >
                <img
                  src={user.avatar || DEFAULT_AVATAR}
                  alt={user.username}
                  onError={(e) => { e.target.src = DEFAULT_AVATAR; }}
                />
                <div className="wa-new-chat-user-info">
                  <h4>{user.username}</h4>
                  <p>{user.about || 'Hey there! I am using WhatsApp'}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Header */}
      <div className="wa-sidebar-header" data-testid="sidebar-header">
        <img
          className="wa-avatar"
          src={currentUser?.avatar || DEFAULT_AVATAR}
          alt="profile"
          onError={(e) => { e.target.src = DEFAULT_AVATAR; }}
        />
        <div className="wa-header-actions">
          <button
            className="wa-icon-btn"
            onClick={() => setShowNewChat(true)}
            title="New Chat"
            data-testid="new-chat-btn"
          >
            <MessageSquarePlus size={20} />
          </button>
          <div style={{ position: 'relative' }}>
            <button
              className="wa-icon-btn"
              onClick={() => setShowMenu(!showMenu)}
              title="Menu"
              data-testid="sidebar-menu-btn"
            >
              <MoreVertical size={20} />
            </button>
            {showMenu && (
              <div className="wa-dropdown-menu" data-testid="sidebar-dropdown">
                <div className="wa-dropdown-item" onClick={() => { setShowMenu(false); }}>
                  New group
                </div>
                <div className="wa-dropdown-item" onClick={() => { setShowMenu(false); }}>
                  Starred messages
                </div>
                <div className="wa-dropdown-item" onClick={() => { setShowMenu(false); }}>
                  Settings
                </div>
                <div
                  className="wa-dropdown-item"
                  onClick={() => { setShowMenu(false); onLogout(); }}
                  data-testid="logout-btn"
                >
                  Log out
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="wa-search-container" data-testid="search-container">
        <div className="wa-search-bar">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search or start a new chat"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            data-testid="search-input"
          />
        </div>
        <button className="wa-filter-btn" data-testid="filter-btn">
          <Filter size={18} />
        </button>
      </div>

      {/* Contact List */}
      <div className="wa-contacts-list" data-testid="contacts-list">
        {filteredConvs.map((conv) => {
          const other = conv.participants?.[0];
          const name = conv.is_group ? conv.group_name : other?.username || 'Unknown';
          const avatar = conv.is_group ? DEFAULT_AVATAR : other?.avatar || DEFAULT_AVATAR;
          const isOnline = other?.is_online;
          const lastMsg = conv.last_message;
          const unread = conv.unread_count || 0;
          const isTyping = typingUsers[conv.conversation_id];
          const isSelected = selectedConv?.conversation_id === conv.conversation_id;

          let preview = 'Start a conversation';
          if (isTyping) {
            preview = null; // handled below
          } else if (lastMsg) {
            preview = lastMsg.content;
          }

          return (
            <div
              key={conv.conversation_id}
              className={`wa-contact-item ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectConv(conv)}
              data-testid={`contact-item-${conv.conversation_id}`}
            >
              <img
                className="wa-contact-avatar"
                src={avatar}
                alt={name}
                onError={(e) => { e.target.src = DEFAULT_AVATAR; }}
              />
              <div className="wa-contact-info">
                <div className="wa-contact-top">
                  <span className="wa-contact-name">{name}</span>
                  <span className={`wa-contact-time ${unread > 0 ? 'has-unread' : ''}`}>
                    {lastMsg ? formatTime(lastMsg.created_at) : ''}
                  </span>
                </div>
                <div className="wa-contact-bottom">
                  {isTyping ? (
                    <span className="wa-typing-indicator">typing...</span>
                  ) : (
                    <span className="wa-contact-preview">{preview}</span>
                  )}
                  {unread > 0 && (
                    <span className="wa-unread-badge" data-testid={`unread-badge-${conv.conversation_id}`}>
                      {unread}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="wa-bottom-encrypt">
        Your personal messages are <a href="#e2e">end-to-end encrypted</a>
      </div>
    </div>
  );
}
