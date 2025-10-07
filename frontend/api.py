from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow calls from React (localhost:3000 in dev)

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
    new_msg = {
        "userName": data["userName"],
    }
    return jsonify(new_msg), 201


if __name__ == "__main__":
    app.run(port=5000, debug=True)
