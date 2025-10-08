from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import send_file
import os

app = Flask(__name__)
CORS(app)  # allow calls from React (localhost:3000 in dev)

users = [
    {"id": 1, "name": "Alice", "avatar": "🟢"},
    {"id": 2, "name": "Bob", "avatar": "🔵"},
    {"id": 3, "name": "Charlie", "avatar": "🟣"},
]

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

username = ""

# --- API Endpoints ---
@app.route("/users", methods=["GET"])
def get_users():
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

@app.route("/users/login/<string:user_name>", methods=["POST"])
def login(user_name):
    data = request.get_json()
    global username
    username = user_name
    return jsonify(username), 201



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