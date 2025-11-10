from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sock import Sock
import json
import os
from peer import Me

app = Flask(__name__)
CORS(app)  # allow calls from React (localhost:3000 in dev)
sock = Sock(app)

avatars = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫"]

# --- Dummy data (moved from React) ---
conversations = {
    1: [
        {"id": 1, "text": "Hey, how are you?", "sender": "other"},
        {"id": 2, "text": "Doing well, working on a project!", "sender": "me"},
        {
            "id": 10001,
            "text": "[file] Alice shared a file: example.txt",
            "sender": "other",
            "isFile": True,
            "filename": "example.txt"
        }
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
    users = {}
    for i, (id, data) in enumerate(peer.known_peers.items()):
        users[id] = {
            "id": id,
            "name": data['name'],
            "avatar": avatars[i % len(avatars)],
        }
    return jsonify(users)

@app.route("/messages/<user_id>", methods=["GET"])
def get_messages(user_id):
    print(username)

    return jsonify(conversations.get(user_id, []))

@app.route("/messages/<user_id>", methods=["POST"])
def send_message(user_id):
    message = request.get_data().decode('utf-8')
    response = {
        "text": message,
        "sender": "me",
    }
    peer.send_message(user_id, message)
    return jsonify(response), 201

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
    return jsonify(username), 201

# --- Logout Endpoint ---
@app.route("/users/logout", methods=["POST"])
def logout():
    """Logs out the current user and clears the username."""
    global username
    username = ""
    return jsonify({"message": "Logged out successfully."}), 200


# Dummy storage for shared files
shared_files = {}  # Maps user_id -> {"filename": ..., "path": ...}

# --- Share File Endpoint ---
@app.route("/share-file/<int:user_id>", methods=["POST"])
def share_file(user_id):
    """Simulate a user sharing a file by registering it in shared_files."""
    file_info = request.get_json()
    filename = file_info.get("filename", "example.txt")
    shared_files[user_id] = {"filename": filename, "path": f"./files/{filename}"}

    # Create a dummy message in conversation
    file_message = {
        "id": len(conversations.get(user_id, [])) + 10000,
        "text": f"{username} shared a file: {filename}",
        "sender": "other",
        "isFile": True,
        "filename": filename,
    }
    conversations.setdefault(user_id, []).append(file_message)
    return jsonify(file_message), 201

# --- Request File Endpoint ---
@app.route("/request-file/<int:user_id>/<string:filename>", methods=["GET"])
def request_file(user_id, filename):
    """Simulate requesting the file from a peer (here we just send a dummy file)."""
    # Create dummy file content
    os.makedirs("files", exist_ok=True)
    filepath = os.path.join("files", filename)
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write("This is a dummy file content.\n")

    # In real system, this would fetch from the peer directly.
    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
