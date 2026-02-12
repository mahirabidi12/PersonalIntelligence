"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { supabase } from "./supabaseClient";
import Auth from "./components/Auth";

type Message = {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  created_at: string;
};

type Contact = {
  id: string;
  name: string;
  img: string;
  nopic: boolean;
  lastMessage: string;
  date: string;
};

const ALL_CONTACTS: Contact[] = [
  {
    id: "user1",
    name: "Saswata",
    img: "/img/109316527.jpg",
    nopic: false,
    lastMessage: "",
    date: "Today",
  },
  {
    id: "user2",
    name: "Ananya",
    img: "/img/girl-profile.jpg",
    nopic: false,
    lastMessage: "",
    date: "Today",
  },
  {
    id: "user3",
    name: "Arjun Mehta",
    img: "/img/arjun-profile.jpg",
    nopic: false,
    lastMessage: "",
    date: "Yesterday",
  },
  {
    id: "user4",
    name: "Priya Sharma",
    img: "/img/79feb1611dddcbce7910e0c1081df6e2.jpg",
    nopic: false,
    lastMessage: "",
    date: "Friday",
  },
  {
    id: "user5",
    name: "Vikram Patel",
    img: "/img/e5wnacz2aaaa.jpg",
    nopic: false,
    lastMessage: "",
    date: "Thursday",
  },
  {
    id: "user6",
    name: "Neha Gupta",
    img: "/img/neha-profile.jpg",
    nopic: false,
    lastMessage: "",
    date: "Wednesday",
  },
  {
    id: "user7",
    name: "Amit Kumar",
    img: "/img/amit-profile.jpg",
    nopic: false,
    lastMessage: "",
    date: "Tuesday",
  },
  {
    id: "user8",
    name: "Rohan Singh",
    img: "/img/rohan-profile.jpg",
    nopic: false,
    lastMessage: "",
    date: "Monday",
  },
  {
    id: "user9",
    name: "Kavita Reddy",
    img: "/img/kavita-profile.jpg",
    nopic: false,
    lastMessage: "",
    date: "02/05",
  },
  {
    id: "user10",
    name: "Dev Team",
    img: "/img/devteam-profile.jpg",
    nopic: false,
    lastMessage: "",
    date: "01/30",
  },
  {
    id: "user11",
    name: "Sanjay Iyer",
    img: "/img/sanjay-profile.jpg",
    nopic: false,
    lastMessage: "",
    date: "01/28",
  },
];

function getConversationId(userId: string, contactId: string) {
  const sorted = [userId, contactId].sort();
  return `${sorted[0]}-${sorted[1]}-chat`;
}

export default function Home() {
  const [userId, setUserId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [selectedContactId, setSelectedContactId] = useState<string | null>(null);
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({});
  const [unreadCounts, setUnreadCounts] = useState<Record<string, number>>({});
  const [readChats, setReadChats] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Filter out the logged-in user from the contacts list
  const contacts = ALL_CONTACTS.filter((c) => c.id !== userId);

  // Auto-select first contact when userId changes
  const effectiveSelectedId = selectedContactId && contacts.some((c) => c.id === selectedContactId)
    ? selectedContactId
    : contacts[0]?.id ?? null;

  const conversationId = userId && effectiveSelectedId
    ? getConversationId(userId, effectiveSelectedId)
    : "";

  const selectedContact = contacts.find((c) => c.id === effectiveSelectedId);

  useEffect(() => {
    const stored = localStorage.getItem("chatUserId");
    if (stored) setUserId(stored);
    setHydrated(true);
  }, []);

  const formattedMessages = useMemo(
    () =>
      messages.map((m) => ({
        ...m,
        time: new Date(m.created_at).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      })),
    [messages]
  );

  // Fetch last message preview and unread counts for each contact
  const fetchLastMessages = useCallback(async () => {
    if (!userId) return;
    const previews: Record<string, string> = {};
    const unreads: Record<string, number> = {};
    for (const contact of ALL_CONTACTS.filter((c) => c.id !== userId)) {
      const convId = getConversationId(userId, contact.id);
      // Fetch recent messages (last 50) to count trailing received
      const { data } = await supabase
        .from("chats")
        .select("sender_id,content")
        .eq("conversation_id", convId)
        .order("created_at", { ascending: false })
        .limit(50);
      if (data && data.length > 0) {
        previews[contact.id] = data[0].content;
        // Count consecutive messages from the contact (trailing received)
        let count = 0;
        for (const msg of data) {
          if (msg.sender_id !== userId) {
            count++;
          } else {
            break;
          }
        }
        if (count > 0) {
          unreads[contact.id] = count;
        }
      }
    }
    setLastMessages(previews);
    setUnreadCounts(unreads);
  }, [userId]);

  // Poll for messages in the selected conversation
  useEffect(() => {
    if (!userId || !conversationId) return;

    const fetchMessages = async () => {
      const { data, error } = await supabase
        .from("chats")
        .select("*")
        .eq("conversation_id", conversationId)
        .order("created_at", { ascending: true });

      if (error) {
        console.error("Error loading messages:", error);
        return;
      }

      if (data) {
        setMessages((prev) => {
          const dbIds = new Set(data.map((m: Message) => m.id));
          const optimistic = prev.filter(
            (m) => m.id.startsWith("temp-") && !dbIds.has(m.id)
          );
          return [...(data as Message[]), ...optimistic];
        });
      }
    };

    fetchMessages();
    const interval = setInterval(fetchMessages, 2000);

    return () => clearInterval(interval);
  }, [userId, conversationId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch last message previews and unread counts on same 2s cycle
  useEffect(() => {
    if (!userId) return;
    fetchLastMessages();
    const interval = setInterval(fetchLastMessages, 2000);
    return () => clearInterval(interval);
  }, [userId, fetchLastMessages]);

  const handleSend = async () => {
    if (!userId) return;
    const content = newMessage.trim();
    if (!content) return;

    const optimisticId = `temp-${Date.now()}`;
    const optimisticMessage: Message = {
      id: optimisticId,
      conversation_id: conversationId,
      sender_id: userId,
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMessage]);
    setNewMessage("");

    const { data, error } = await supabase
      .from("chats")
      .insert({
        conversation_id: conversationId,
        sender_id: userId,
        content,
      })
      .select()
      .single();

    if (error) {
      console.error("Error sending message:", error);
      setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
      setNewMessage(content);
      return;
    }

    if (data) {
      setMessages((prev) =>
        prev.map((m) => (m.id === optimisticId ? (data as Message) : m))
      );
      if (effectiveSelectedId) {
        setLastMessages((prev) => ({ ...prev, [effectiveSelectedId]: content }));
      }
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("chatUserId");
    setUserId(null);
    setMessages([]);
  };

  const handleSelectContact = (contactId: string) => {
    setSelectedContactId(contactId);
    setMessages([]);
    setNewMessage("");
    setReadChats((prev) => ({ ...prev, [contactId]: true }));
  };

  if (!hydrated) {
    return (
      <div style={{ minHeight: "100vh", background: "#111b21" }} />
    );
  }

  if (!userId) {
    return <Auth onSelect={(id) => { localStorage.setItem("chatUserId", id); setUserId(id); }} />;
  }

  const handleKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="container">
      <div className="whatsapp">
        <div className="contacts">
          <div className="connav navs">
            <div className="profile" title={userId}>
              <img src={userId === "user1" ? "/img/109316527.jpg" : "/img/e5wnacz2aaaa.jpg"} alt="" />
            </div>
            <div className="tools">
              <div className="tool" title="People">
                <img src="/img/icons8-people-64.png" alt="" />
              </div>
              <div className="tool" title="Status">
                <img src="/img/icons8-loading-50.png" alt="" />
              </div>
              <div className="tool" title="New Chat">
                <img src="/img/icons8-typing-96.png" alt="" />
              </div>
              <div
                className="tool"
                onClick={handleSignOut}
                style={{ cursor: "pointer" }}
                title="Sign Out"
              >
                <img src="/img/icons8-menu-vertical-50.png" alt="" />
              </div>
            </div>
          </div>
          <div className="search">
            <div className="searchBar">
              <img src="/img/icons8-search-64.png" alt="" />
              <img src="/img/icons8-back-96.png" alt="" />
              <input
                type="text"
                placeholder="Search Chat"
              />
            </div>
            <img src="/img/icons8-grip-lines-96.png" alt="" />
          </div>
          <div className="usersContainer">
            <div className="users">
              {contacts.map((contact) => {
                const preview = lastMessages[contact.id] || contact.lastMessage || "Start a conversation";
                const unread = readChats[contact.id] ? 0 : (unreadCounts[contact.id] || 0);
                return (
                  <div
                    className={`user${effectiveSelectedId === contact.id ? " selected" : ""}`}
                    key={contact.id}
                    onClick={() => handleSelectContact(contact.id)}
                  >
                    <div className={`pfp${contact.nopic ? " nopic" : ""}`}>
                      <img src={contact.img} alt="" />
                    </div>
                    <div className="userinfo">
                      <div className="name">
                        <p>{contact.name}</p>
                      </div>
                      <div className="message">
                        <div className="meicon">
                          <p>{preview}</p>
                          <div className="arrow">
                            <img src="/img/icons8-expand-arrow-96.png" alt="" />
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="userdate">
                      <p className={unread > 0 ? "unread-date" : ""}>{contact.date}</p>
                      {unread > 0 ? (
                        <span className="unread-badge">{unread}</span>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="bottomcon">
              <p>
                Your personal messages are{" "}
                <a href="#">end-to-end encrypted</a>
              </p>
            </div>
          </div>
        </div>
        <div className="conversation">
          <div className="convenav navs">
            <div className="conveuser">
              <div className="profile">
                <img
                  src={selectedContact?.img ?? "/img/icons8-account-96.png"}
                  alt=""
                />
              </div>
              <div className="profileInformation">
                <h4>{selectedContact?.name ?? ""}</h4>
                <p>online</p>
              </div>
            </div>
            <div className="tools">
              <div className="tool">
                <img src="/img/icons8-search-64.png" alt="" />
              </div>
              <div className="tool">
                <img src="/img/icons8-menu-vertical-50.png" alt="" />
              </div>
            </div>
          </div>
          <div className="convemessages">
            {formattedMessages.length === 0 ? (
              <div className="middle">
                <p>No messages yet. Send one!</p>
              </div>
            ) : (
              formattedMessages.map((message) =>
                message.sender_id === userId ? (
                  <div
                    className="senderContainer arrowm"
                    key={message.id}
                  >
                    <div className="sender mepop">
                      <div className="thereply">
                        <p>{message.content}</p>
                        <div className="time">
                          <p>{message.time}</p>
                          <img src="/img/icons8-double-tick-96.png" alt="" />
                        </div>
                        <div className="arrowhover arrowG">
                          <img src="/img/icons8-expand-arrow-96.png" alt="" />
                        </div>
                        <div className="react rightr">
                          <img src="/img/icons8-happy-96.png" alt="" />
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div
                    className="receiverContainer arrowm"
                    key={message.id}
                  >
                    <div className="reciver mepop">
                      <div className="thereply">
                        <p>{message.content}</p>
                        <div className="time">
                          <p>{message.time}</p>
                        </div>
                        <div className="arrowhover arrowW">
                          <img src="/img/icons8-expand-arrow-96.png" alt="" />
                        </div>
                        <div className="react leftr">
                          <img src="/img/icons8-happy-96.png" alt="" />
                        </div>
                      </div>
                    </div>
                  </div>
                )
              )
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className="convebottom">
            <div className="tools">
              <div className="tool">
                <img src="/img/icons8-smiling-90.png" alt="" />
              </div>
              <div className="tool">
                <img src="/img/icons8-attach-100.png" alt="" />
              </div>
            </div>
            <input
              type="text"
              placeholder="Type a message"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <div className="tool" onClick={handleSend}>
              <img src="/img/icons8-microphone-96.png" alt="" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
