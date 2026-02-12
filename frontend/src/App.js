import React, { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import LoginPage from './components/LoginPage';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import EmptyChat from './components/EmptyChat';

const API_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [token, setToken] = useState(localStorage.getItem('wa2_token'));
  const [currentUser, setCurrentUser] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [selectedConv, setSelectedConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [users, setUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const wsRef = useRef(null);

  const fetchMe = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/auth/me?authorization=Bearer ${token}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentUser(data);
      } else {
        handleLogout();
      }
    } catch (e) {
      console.error('Failed to fetch user', e);
    }
  }, [token]);

  const fetchConversations = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/conversations?authorization=Bearer ${token}`);
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (e) {
      console.error('Failed to fetch conversations', e);
    }
  }, [token]);

  const fetchUsers = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/users?authorization=Bearer ${token}`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (e) {
      console.error('Failed to fetch users', e);
    }
  }, [token]);

  const fetchMessages = useCallback(async (convId) => {
    if (!token || !convId) return;
    try {
      const res = await fetch(`${API_URL}/api/messages/${convId}?authorization=Bearer ${token}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error('Failed to fetch messages', e);
    }
  }, [token]);

  // WebSocket connection
  useEffect(() => {
    if (!token) return;

    const wsProtocol = API_URL.startsWith('https') ? 'wss' : 'ws';
    const wsUrl = `${wsProtocol}://${API_URL.replace(/^https?:\/\//, '')}/api/ws/${token}`;

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'new_message') {
          setMessages(prev => {
            if (prev.length > 0 && prev[0]?.conversation_id === data.conversation_id) {
              return [...prev, data];
            }
            return prev;
          });
          fetchConversations();
        } else if (data.type === 'messages_read') {
          setMessages(prev =>
            prev.map(m => {
              if (m.conversation_id === data.conversation_id && !m.read_by?.includes(data.read_by)) {
                return { ...m, read_by: [...(m.read_by || []), data.read_by] };
              }
              return m;
            })
          );
        } else if (data.type === 'typing') {
          setTypingUsers(prev => ({ ...prev, [data.conversation_id]: data.user_id }));
        } else if (data.type === 'stop_typing') {
          setTypingUsers(prev => {
            const copy = { ...prev };
            delete copy[data.conversation_id];
            return copy;
          });
        } else if (data.type === 'user_online' || data.type === 'user_offline') {
          fetchUsers();
          fetchConversations();
        }
      };

      ws.onclose = () => {
        setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [token, fetchConversations, fetchUsers]);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  useEffect(() => {
    if (currentUser) {
      fetchConversations();
      fetchUsers();
    }
  }, [currentUser, fetchConversations, fetchUsers]);

  useEffect(() => {
    if (selectedConv) {
      fetchMessages(selectedConv.conversation_id);
      // Mark messages as read
      fetch(`${API_URL}/api/messages/read?authorization=Bearer ${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: selectedConv.conversation_id }),
      }).then(() => fetchConversations());
    }
  }, [selectedConv, token, fetchMessages, fetchConversations]);

  const handleLogin = (tokenVal, userData) => {
    localStorage.setItem('wa2_token', tokenVal);
    setToken(tokenVal);
    setCurrentUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('wa2_token');
    setToken(null);
    setCurrentUser(null);
    setConversations([]);
    setMessages([]);
    setSelectedConv(null);
    if (wsRef.current) wsRef.current.close();
  };

  const handleSendMessage = async (content) => {
    if (!selectedConv || !content.trim()) return;

    const optimistic = {
      message_id: `temp-${Date.now()}`,
      conversation_id: selectedConv.conversation_id,
      sender_id: currentUser.user_id,
      content: content.trim(),
      message_type: 'text',
      created_at: new Date().toISOString(),
      read_by: [currentUser.user_id],
    };

    setMessages(prev => [...prev, optimistic]);

    try {
      const res = await fetch(`${API_URL}/api/messages?authorization=Bearer ${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: selectedConv.conversation_id,
          content: content.trim(),
        }),
      });

      if (res.ok) {
        const msg = await res.json();
        setMessages(prev => prev.map(m => m.message_id === optimistic.message_id ? msg : m));
        fetchConversations();
      }
    } catch (e) {
      console.error('Failed to send message', e);
      setMessages(prev => prev.filter(m => m.message_id !== optimistic.message_id));
    }
  };

  const handleStartChat = async (userId) => {
    try {
      const res = await fetch(`${API_URL}/api/conversations?authorization=Bearer ${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ participant_ids: [userId] }),
      });

      if (res.ok) {
        const data = await res.json();
        await fetchConversations();
        const conv = conversations.find(c => c.conversation_id === data.conversation_id);
        if (conv) {
          setSelectedConv(conv);
        } else {
          // Refetch and find
          const convRes = await fetch(`${API_URL}/api/conversations?authorization=Bearer ${token}`);
          if (convRes.ok) {
            const convs = await convRes.json();
            setConversations(convs);
            const newConv = convs.find(c => c.conversation_id === data.conversation_id);
            if (newConv) setSelectedConv(newConv);
          }
        }
      }
    } catch (e) {
      console.error('Failed to start chat', e);
    }
  };

  const sendTyping = (conversationId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'typing', conversation_id: conversationId }));
    }
  };

  const sendStopTyping = (conversationId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop_typing', conversation_id: conversationId }));
    }
  };

  if (!token || !currentUser) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <div className="wa-container" data-testid="whatsapp-main-container">
      <div className="wa-header-strip" />
      <div className="wa-app">
        <Sidebar
          conversations={conversations}
          selectedConv={selectedConv}
          onSelectConv={setSelectedConv}
          currentUser={currentUser}
          onLogout={handleLogout}
          users={users}
          onStartChat={handleStartChat}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          typingUsers={typingUsers}
        />
        {selectedConv ? (
          <ChatPanel
            conversation={selectedConv}
            messages={messages}
            currentUser={currentUser}
            onSendMessage={handleSendMessage}
            typingUsers={typingUsers}
            sendTyping={sendTyping}
            sendStopTyping={sendStopTyping}
          />
        ) : (
          <EmptyChat />
        )}
      </div>
    </div>
  );
}

export default App;
