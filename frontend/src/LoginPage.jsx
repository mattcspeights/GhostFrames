import React, { useState } from "react";
import logo from "./lockheed.png";

export default function LoginPage({ onLogin }) {
  const [name, setName] = useState("");

  const handleSubmit = () => {
    if (name.trim() !== "") {
      onLogin(name);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center w-screen h-screen bg-gray-800 text-white fixed top-0 left-0">
      <img src={logo} alt="logo" className="h-24 w-24 mb-6" />
      <h1 className="text-3xl font-bold mb-4">Welcome to GhostframeSMS</h1>
      <p className="mb-6 text-gray-300">Enter your name to start chatting</p>

      <div className="flex flex-row gap-3">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder="Your name"
          className="px-4 py-2 border rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSubmit}
          className="px-4 py-2 bg-blue-500 rounded-lg hover:bg-blue-600"
        >
          Join
        </button>
      </div>
    </div>
  );
}
