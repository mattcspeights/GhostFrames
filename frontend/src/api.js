const API_URL = "http://localhost:5000";

export async function getUsers() {
  const res = await fetch(`${API_URL}/users`);
  return res.json();
}

export async function getMessages(userId) {
  const res = await fetch(`${API_URL}/messages/${userId}`);
  return res.json();
}

export async function sendMessage(userId, text) {
  // returns 204
  await fetch(`${API_URL}/messages/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: text,
  });
}

export async function login(userName) {
  const res = await fetch(`${API_URL}/users/login/${userName}`,{
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userName }),
  });
  return res.json();
}

export async function shareFile(recipientId, file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("recipientId", recipientId);

  const response = await fetch("/shareFile", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) throw new Error("File share failed");
  return await response.json(); // should return { id, name, sender }
}

export async function requestFile(fileId) {
  const response = await fetch(`/requestFile/${fileId}`);
  if (!response.ok) throw new Error("File request failed");

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);

  // trigger download
  const a = document.createElement("a");
  a.href = url;
  a.download = fileId;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

class Ws {
  constructor(url) {
    this.url = url;
    this.ws = new WebSocket(url);
    this.listeners = [];

    this.ws.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      for (const listener of this.listeners) {
        listener(data);
      }
    });
  }

  onMessage(callback) {
    this.listeners.push(callback);
  }
}

export function ws() {
  return new Ws(`${API_URL.replace('http', 'ws')}/ws/chat`);
}
