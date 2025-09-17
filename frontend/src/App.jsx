import React, { useState, useEffect } from "react";
import logo from "./lockheed.png";
import { getUsers, getMessages, sendMessage as apiSendMessage } from "./api";

export default function App() {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [conversations, setConversations] = useState({});
  const [newMessage, setNewMessage] = useState("");

  // Load users on mount
  useEffect(() => {
    getUsers().then((data) => {
      setUsers(data);
      if (data.length > 0) {
        setSelectedUser(data[0].id);
      }
    });
  }, []);

  // Load messages when user changes
  useEffect(() => {
    if (selectedUser) {
      getMessages(selectedUser).then((msgs) => {
        setConversations((prev) => ({ ...prev, [selectedUser]: msgs }));
      });
    }
  }, [selectedUser]);

  const currentMessages = conversations[selectedUser] || [];

  const handleSend = async () => {
    if (newMessage.trim() === "") return;

    const msg = await apiSendMessage(selectedUser, newMessage);

    setConversations((prev) => ({
      ...prev,
      [selectedUser]: [...(prev[selectedUser] || []), msg],
    }));

    setNewMessage("");
  };

  return (
    <div className="flex flex-col w-screen h-screen bg-gray-700 absolute top-0 left-0">
      {/* Top Bar */}
      <div className="w-full h-10 bg-lockheed-blue text-white flex flex-row">
        <img src={logo} alt="logo" />
        <div className="p-2">GhostframeSMS</div>
      </div>
      <div className="flex h-full">
        {/* Sidebar */}
        <div className="w-1/4 bg-white border-r shadow-md">
          <div className="p-4 font-bold text-lg border-b">Chats</div>
          <ul>
            {users.map((user) => (
              <li
                key={user.id}
                onClick={() => setSelectedUser(user.id)}
                className={`flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-100 ${
                  selectedUser === user.id ? "bg-gray-200 font-semibold" : ""
                }`}
              >
                <span className="text-xl">{user.avatar}</span>
                <span>{user.name}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Chat Window */}
        <div className="flex flex-col flex-1">
          {/* Header */}
          <div className="bg-lockheed-blue text-white p-4 font-semibold">
            {users.find((u) => u.id === selectedUser)?.name}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {currentMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${
                  msg.sender === "me" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`px-4 py-2 rounded-2xl max-w-xs ${
                    msg.sender === "me"
                      ? "bg-lockheed-blue text-white rounded-br-none"
                      : "bg-gray-800 text-white rounded-bl-none"
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="flex p-3 bg-lockheed-blue text-black">
            <input
              type="text"
              placeholder="Type a message..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              className="flex-1 px-4 py-2 border rounded-xl focus:outline-none"
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button
              onClick={handleSend}
              className="ml-2 px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
