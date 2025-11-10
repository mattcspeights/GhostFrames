import React, { useState, useEffect } from "react";
import { HashRouter, Routes, Route, useNavigate } from "react-router-dom";
import { getUsers, getMessages, sendMessage, login, ws } from "./api";
import ChatWindow from "./ChatWindow";
import LoginPage from "./LoginPage";

function ChatRoute({ userName, onLogout }) {
  const [users, setUsers] = useState({});
  const [selectedUser, setSelectedUser] = useState(null);
  const [conversations, setConversations] = useState({});
  const navigate = useNavigate();

  /**
   * Updates the UI when a new message is received via WebSocket, adding it
   * to the appropriate conversation.
   */
  function onMessage(message) {
    const { from, text } = message;
    setConversations((prev) => ({
      ...prev,
      [from]: [...(prev[from] || []), { id: from, text, sender: "them" }],
    }));
  }

  // Redirect if not logged in
  useEffect(() => {
    if (!userName) navigate("/");
  }, [userName, navigate]);

  // Initialize WebSocket and fetch users on component mount
  useEffect(() => {
    async function init() {
      const websocket = await ws();
      websocket.onMessage(onMessage);

      const data = await getUsers();
      setUsers(data);

      const ids = Object.keys(data);
      if (ids.length > 0) setSelectedUser(ids[0]);
    }
    init();
  }, []);

  // Load messages when selected user changes
  useEffect(() => {
    async function init() {
      const websocket = await ws();
      websocket.onMessage(onMessage);

      const data = await getUsers();
      setUsers(data);
    }
    init();
  }, []);

  const handleSend = async (text) => {
    if (!text.trim() || !selectedUser) return;
    const msg = await sendMessage(selectedUser, text);
    setConversations((prev) => ({
      ...prev,
      [selectedUser]: [...(prev[selectedUser] || []), msg],
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
