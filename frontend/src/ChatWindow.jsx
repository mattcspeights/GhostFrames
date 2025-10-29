import React, { useState } from "react";
import { shareFile, requestFile } from "./api";
import logo from "./lockheed.png";
import { useNavigate } from "react-router-dom";

export default function ChatWindow({
  users,
  selectedUser,
  setSelectedUser,
  conversations,
  onSend,
  userName,
  onLogout,
}) {

  const navigate = useNavigate(); // <-- add this

  const handleLogout = async () => {
    await fetch("http://localhost:5000/users/logout", { method: "POST" });
    if (onLogout) onLogout(); // reset App state
    navigate("/"); // <-- navigate to login page
  };

  const [newMessage, setNewMessage] = useState("");
  const [file, setFile] = useState(null);
  const currentMessages = conversations[selectedUser] || [];

  const handleSend = () => {
    if (newMessage.trim()) {
      onSend(newMessage);
      setNewMessage("");
    }
  };

  const handleFileSelect = (e) => {
    setFile(e.target.files[0]);
  };

  const handleFileShare = async () => {
    if (!file) return;
    const msg = await shareFile(selectedUser, file);

    // Add a "file shared" message to the conversation
    onSend(`[file]${msg.name}:${msg.id}`);
    setFile(null);
  };

  const handleRequestFile = async (fileId) => {
    await requestFile(fileId);
  };

  const renderMessage = (msg) => {
    if (msg.text.startsWith("[file]")) {
      const [_, fileName, fileId] = msg.text.match(/\[file\](.*?):(.*)/);
      return (
        <div>
          <div>{fileName}</div>
          <button
            onClick={() => handleRequestFile(fileId)}
            className="mt-1 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            Request File
          </button>
        </div>
      );
    }
    return msg.text;
  };

  return (
    <div className="flex flex-col w-screen h-screen bg-gray-700 absolute top-0 left-0">
      {/* Top Bar */}
      <div className="w-full h-12 bg-lockheed-blue text-white flex flex-row items-center justify-between px-4">
        <div className="flex flex-row items-center gap-2">
          <img src={logo} alt="logo" className="h-12 w-12" />
          <div className="text-lg font-semibold">GhostframeSMS</div>
        </div>
        <div className="flex flex-row items-center gap-2">
          <label className="p-2">Name: {userName}</label>
          <button
          onClick={handleLogout}
          className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded-md text-sm"
          >
          Logout
          </button>
        </div>
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
                  {renderMessage(msg)}
                </div>
              </div>
            ))}
          </div>

          {/* Input + Attach */}
          <div className="flex p-3 bg-lockheed-blue text-black items-center">
            <input
              type="text"
              placeholder="Type a message..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              className="flex-1 px-4 py-2 border rounded-xl focus:outline-none"
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />

            {/* Hidden file input */}
            <input
              type="file"
              id="fileInput"
              className="hidden"
              onChange={handleFileSelect}
            />
            <label
              htmlFor="fileInput"
              className="ml-2 px-3 py-2 bg-gray-300 rounded-xl cursor-pointer hover:bg-gray-400"
            >
              📎
            </label>

            <button
              onClick={file ? handleFileShare : handleSend}
              className="ml-2 px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600"
            >
              {file ? "Share" : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
