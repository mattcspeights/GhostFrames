import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { getUsers, getMessages, sendMessage, login } from "./api";
import ChatWindow from "./ChatWindow";
import LoginPage from "./LoginPage";

function ChatRoute({ userName, onLogout }) {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [conversations, setConversations] = useState({});
  const navigate = useNavigate();

  // Redirect if not logged in
  useEffect(() => {
    if (!userName) navigate("/");
  }, [userName, navigate]);

  // Load users on mount
  useEffect(() => {
    getUsers().then((data) => {
      setUsers(data);
      if (data.length > 0) setSelectedUser(data[0].id);
    });
  }, []);

  // Load messages when selected user changes
  useEffect(() => {
    if (selectedUser) {
      getMessages(selectedUser).then((msgs) => {
        setConversations((prev) => ({ ...prev, [selectedUser]: msgs }));
      });
    }
  }, [selectedUser]);

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
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  );
}
