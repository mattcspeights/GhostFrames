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
  const res = await fetch(`${API_URL}/messages/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, sender: "me" }),
  });
  return res.json();
}

export async function login(userName) {
  const res = await fetch(`${API_URL}/users/login/${userName}`,{
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({userName}),
  });
  return res.json();
}
