import React, { useState, useEffect, useRef } from "react";
import { HashRouter, Routes, Route, useNavigate } from "react-router-dom";
import { getUsers, getMessages, sendMessage, login, ws } from "./api";
import ChatWindow from "./ChatWindow";
import LoginPage from "./LoginPage";

function ChatRoute({ userName, onLogout }) {
  const connection = useRef(null);
  const [users, setUsers] = useState({});
  const [selectedUser, setSelectedUser] = useState(null);
  const [conversations, setConversations] = useState({});
  const navigate = useNavigate();

  /**
   * Updates the UI when a new message is received via WebSocket, adding it
   * to the appropriate conversation.
   * @param {{type: 'peer_joined', peer_id: string, peer_name: string} | {type: 'message', from: string, text: string}} event
   */
  function onEvent(event) {
    switch (event.type) {
      case "peer_joined": {
        const avatars = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫"];
        setUsers((prev) => ({
          ...prev,
          [event.peer_id]: { id: event.peer_id, name: event.peer_name, avatar: avatars[Math.floor(Math.random() * avatars.length)] },
        }));
        break;
      }

      case "message": {
        const { from, text } = event;
        setConversations((prev) => ({
          ...prev,
          [from]: [...(prev[from] || []), { id: from, text, sender: "them" }],
        }));
        break;
      }

      default:
        console.warn("Unknown event type:", event.type);
    }
  }

  // Redirect if not logged in
  useEffect(() => {
    if (!userName) navigate("/");
  }, [userName, navigate]);

  // Initialize WebSocket
  useEffect(() => {
    const websocket = ws();
    connection.current = websocket;
    websocket.onEvent(onEvent);
    return () => {
      websocket.close();
    };
  }, []);

  // Fetch users on component mount
  useEffect(() => {
    async function init() {
      const data = await getUsers();
      setUsers(data);

      const ids = Object.keys(data);
      if (ids.length > 0) setSelectedUser(ids[0]);
    }
    init();
  }, []);

  const handleSend = async (text) => {
    if (!text.trim() || !selectedUser) return;
    await sendMessage(selectedUser, text);
    setConversations((prev) => ({
      ...prev,
      [selectedUser]: [...(prev[selectedUser] || []), { id: selectedUser, text, sender: "me" }],
    }));
  };

  return (
    <ChatWindow
      users={users}
      selectedUser={selectedUser}
      setSelectedUser={setSelectedUser}
      conversations={conversations}
      onSend={handleSend}
      userName={userName}
      onLogout={onLogout}
    />
  );
}

function AppInner() {
  const [userName, setUserName] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (name) => {
    if (!name.trim()) return;
    await login(name);
    setUserName(name);
    navigate("/chat"); // ✅ navigate after login
  };

  const handleLogout = async () => {
    await fetch("http://localhost:5000/users/logout", { method: "POST" });
    setUserName("");
    navigate("/"); // ✅ navigate back to login
  };

  return (
    <Routes>
      <Route path="/" element={<LoginPage onLogin={handleLogin} />} />
      <Route
        path="/chat"
        element={<ChatRoute userName={userName} onLogout={handleLogout} />}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <HashRouter>
      <AppInner />
    </HashRouter>
  );
}
