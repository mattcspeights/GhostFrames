from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock
import json
from peer import Me

app = Flask(__name__)
CORS(app)  # allow calls from React (localhost:3000 in dev)
sock = Sock(app)

avatars = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫"]

# --- Dummy data (moved from React) ---
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

username = "Anonymous"
peer = Me(username)
peer.start()

# --- API Endpoints ---
@app.route("/users", methods=["GET"])
def get_users():
    print(peer.known_peers)
    # use these peers with random avatars
    users = []
    for i, p in enumerate(peer.known_peers):
        users.append({
            "id": i + 1,
            "name": p,
            "avatar": avatars[i % len(avatars)],
        })
    return jsonify(users)

@app.route("/messages/<int:user_id>", methods=["GET"])
def get_messages(user_id):
    print(username)

    return jsonify(conversations.get(user_id, []))

@app.route("/messages/<int:user_id>", methods=["POST"])
def send_message(user_id):
    data = request.get_json()
    print(data.get("id",0))
    new_msg = {
        "id": int(data.get("id", 0)) or len(conversations.get(user_id, [])) + 1000,
        "text": data["text"],
        "sender": data.get("sender", "me"),
    }
    conversations.setdefault(user_id, []).append(new_msg)
    return jsonify(new_msg), 201

@sock.route('/ws/chat')
def chat(ws):
    def handle_message(sender_id, message):
        msg = {
            "from": sender_id,
            "text": message,
        }
        ws.send(json.dumps(msg))

    peer.register_message_listener(handle_message)

    try:
        while True:
            data = ws.receive() # Don't care about incoming data
            if data is None:
                break
    except Exception as e:
        print("WebSocket error:", e)
    finally:
        print("WebSocket connection ended")

@app.route("/users/login/<string:new_username>", methods=["POST"])
def login(new_username):
    '''
    Set the global username for the session.
    '''
    global username
    username = new_username
    peer.id = new_username
    peer.name = new_username

    new_msg = {
        "userName": new_username
    }
    return jsonify(new_msg), 201


if __name__ == "__main__":
    app.run(port=5000, debug=True)
