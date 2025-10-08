#FLASK API
from flask import Flask, request, jsonify
from flask_cors import CORS

#PEER
import json
import random
import socket
import time
import threading

BROADCAST_PORT = 65432
CHAT_PORT = int(random.uniform(20000, 30000))
NAME = ""

def decode_msg(data):
    return json.loads(data.decode())

def encode_msg(msg) -> bytes:
    return json.dumps(msg).encode()

class Me:
    '''
    Handles a connection to the local network.
    '''
    def __init__(self):
        self.name = ""

        self.known_peers = {}
        self.conversations = {}

        self.scan_for_peers_thread = threading.Thread(target=self.scan_for_peers, daemon=True)
        self.scan_for_dms_thread = threading.Thread(target=self.scan_for_dms, daemon=True)
        self.announcer_thread = threading.Thread(target=self.announcer, daemon=True)

    def scan_for_peers(self):
        '''
        Listens for peer announcements and updates the known peers list. Should
        be run in a separate thread.
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', BROADCAST_PORT))
        while True:
            data, addr = sock.recvfrom(1024)
            msg = decode_msg(data)
            if msg['id'] == ID:
                continue
            if msg['type'] == 'announce':
                self.known_peers[msg['id']] = {
                    'name': msg['name'],
                    'addr': addr,
                    'port': msg['port'],
                    'last_seen': time.time(),
                }

    def scan_for_dms(self):
        '''
        Listens for direct messages from peers and store them to conversations
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', CHAT_PORT))
        while True:
            data, addr = sock.recvfrom(1024)
            msg = decode_msg(data)
            if msg['type'] == 'msg':
                sender_name = self.known_peers.get(msg['from'], {'name': 'Unknown'})['name']
                content = msg['text']
                print(f'{sender_name} -> {self.name}: {content}')

    def announcer(self):
        '''
        Periodically announces presence to other peers over the local network.
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = encode_msg({
            'id': self.name,
            'type': 'announce',
            'name': self.name,
            'port': CHAT_PORT,
        })
        while True:
            sock.sendto(msg, ('<broadcast>', BROADCAST_PORT))
            time.sleep(2)

    def send_message(self, id, text):
        '''
        Sends a direct message to a known peer. Prints an error if the peer
        ID is not known.
        '''
        if id not in self.known_peers:
            print('Unknown peer ID')
            return
        peer = self.known_peers[id]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = encode_msg({
            'type': 'msg',
            'from': self.name,
            'text': text,
        })
        sock.sendto(msg, (peer['addr'][0], peer['port']))
        peer_name = peer['name']
        print(f'{self.name} -> {peer_name}: {text}')

    def start(self):
        '''
        Starts the connection threads and enters the command loop.
        '''
        self.scan_for_peers_thread.start()
        self.scan_for_dms_thread.start()
        self.announcer_thread.start()

        print('''Commands:
ls                 = list known peers
msg <id> <message> = send message to peer''')

        while True:
            print()
            cmd = input('''> ''')
            parts = cmd.split(' ', 2)
            if parts[0] == 'ls':
                for id, info in self.known_peers.items():
                    name = info['name']
                    last_seen_secs = time.time() - info['last_seen']
                    print(f'{name} ({id}) last seen {last_seen_secs}s ago')
            elif parts[0] == 'msg' and len(parts) == 3:
                self.send_message(parts[1], parts[2])
            else:
                print('Unknown command')



app = Flask(__name__)
me = Me(NAME)
CORS(app)  # allow calls from React (localhost:3000 in dev)

users = [
    # {"id": 1, "name": "Alice", "avatar": "🟢"},
    # {"id": 2, "name": "Bob", "avatar": "🔵"},
    # {"id": 3, "name": "Charlie", "avatar": "🟣"},
]

conversations = {
    # 1: [
    #     {"id": 1, "text": "Hey, how are you?", "sender": "other"},
    #     {"id": 2, "text": "Doing well, working on a project!", "sender": "me"},
    # ],
    # 2: [
    #     {"id": 3, "text": "Yo, wanna play later?", "sender": "other"},
    #     {"id": 4, "text": "Sure, I’m free tonight.", "sender": "me"},
    # ],
    # 3: [
    #     {"id": 5, "text": "Don’t forget the meeting tomorrow.", "sender": "other"},
    # ],
}


# --- API Endpoints ---
@app.route("/users", methods=["GET"])
def get_users():
    return jsonify(me.known_peers)

@app.route("/messages/<string:user_id>", methods=["GET"])
def get_messages(user_id):
    return jsonify(me.conversations.get(user_id, []))

@app.route("/messages/<string:user_id>", methods=["POST"])
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

    me = Me(user_name)
    me.start()
    return jsonify(new_msg), 201

def run_flask():
    app.run(port=5000, debug=True)

def run_peer():
    me.start()

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    
