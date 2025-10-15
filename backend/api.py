# backend/api.py
import argparse, json, logging, socket
from contextlib import closing
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Dev-friendly; for production you can restrict origins if you like.
CORS(app)

# --- Dummy data (same as before) ---
users = [
    {"id": 1, "name": "Alice", "avatar": "🟢"},
    {"id": 2, "name": "Bob", "avatar": "🔵"},
    {"id": 3, "name": "Charlie", "avatar": "🟣"},
]
conversations = {
    1: [
        {"id": 1, "text": "Hey, how are you?", "sender": "other"},
        {"id": 2, "text": "Doing well, working on a project!", "sender": "me"},
    ],
    2: [
        {"id": 3, "text": "Yo, wanna play later?", "sender": "other"},
        {"id": 4, "text": "Sure, I’m free tonight.", "sender": "me"},
    ],
    3: [
        {"id": 5, "text": "Don’t forget the meeting tomorrow.", "sender": "other"},
    ],
}
username = ""

# --- Routes ---
@app.get("/health")
def health():
    return jsonify(ok=True)

@app.get("/users")
def get_users():
    return jsonify(users)

@app.get("/messages/<int:user_id>")
def get_messages(user_id):
    app.logger.debug("username=%s", username)
    return jsonify(conversations.get(user_id, []))

@app.post("/messages/<int:user_id>")
def send_message(user_id):
    data = request.get_json(force=True) or {}
    new_id = int(data.get("id") or 0) or (len(conversations.get(user_id, [])) + 1000)
    new_msg = {
        "id": new_id,
        "text": data.get("text", ""),
        "sender": data.get("sender", "me"),
    }
    conversations.setdefault(user_id, []).append(new_msg)
    return jsonify(new_msg), 201

@app.post("/users/login/<string:user_name>")
def login(user_name):
    # path param wins; body is optional
    data = request.get_json(silent=True) or {}
    global username
    username = user_name
    return jsonify({"userName": data.get("userName", user_name)}), 201

# --- Process/bootstrap helpers ---
def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def parse_args():
    p = argparse.ArgumentParser(description="Flask backend for Electron")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=0)  # 0 = pick an open port
    p.add_argument("--print-port", action="store_true",
                   help="Print {'host', 'port'} as one JSON line to stdout")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    port = args.port or find_free_port()
    if args.print_port:
        # One line so Electron can parse with a single 'data' event
        print(json.dumps({"host": args.host, "port": port}), flush=True)

    # No debug, no reloader — stable under PyInstaller & Electron spawn
    app.run(host=args.host, port=port, debug=False, use_reloader=False, threaded=True)
