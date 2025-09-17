import json
import socket
import time
import threading

CHAT_PORT = 5000
NAME = input('What\'s your name? ')
# ID = f'{NAME}-{int(time.time())}'
ID = f'{NAME}' # TODO: make unique

peers = {}

def listener():
    '''
    Listens for incoming messages and peer announcements.
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 65432))
    while True:
        data, addr = sock.recvfrom(1024)
        msg = json.loads(data.decode())
        if msg["type"] == "announce":
            peers[msg["id"]] = {"name": msg["name"], "addr": addr, "last_seen": time.time()}
        elif msg["type"] == "msg":
            print(f"{msg['from']} says: {msg['text']}")

def announcer():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = json.dumps({"id": ID, "type": "announce", "name": NAME, "port": CHAT_PORT}).encode()
    while True:
        sock.sendto(msg, ("<broadcast>", 65432))
        time.sleep(2)

def send_message(id, text):
    if id not in peers:
        print("Unknown peer ID")
        return
    peer = peers[id]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = json.dumps({"type": "msg", "from": NAME, "text": text}).encode()
    # sock.sendto(msg, peer["addr"])
    sock.sendto(msg, ("<broadcast>", 65432))
    print(f'To {peer['name']}: {text}')

# start threads
threading.Thread(target=listener, daemon=True).start()
threading.Thread(target=announcer, daemon=True).start()

print('''Commands:
ls                 = list known peers
msg <id> <message> = send message to peer''')

while True:
    print()
    cmd = input('''> ''')
    parts = cmd.split(' ', 2)
    if parts[0] == 'ls':
        for id, info in peers.items():
            print(f"{info['name']} ({id}) last seen {time.time() - info['last_seen']:.1f}s ago")
    elif parts[0] == 'msg' and len(parts) == 3:
        send_message(parts[1], parts[2])
    else:
        print("Unknown command")
