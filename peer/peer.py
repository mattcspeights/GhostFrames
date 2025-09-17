import json
import random
import socket
import time
import threading

BROADCAST_PORT = 65432
CHAT_PORT = int(random.uniform(20000, 30000))
NAME = input('What\'s your name? ')
# ID = f'{NAME}-{int(time.time())}'
ID = f'{NAME}' # TODO: make unique

peers = {}

def decode_msg(data):
    return json.loads(data.decode())

def encode_msg(msg) -> bytes:
    return json.dumps(msg).encode()

def scan_for_peers():
    '''
    Listens for peer announcements.
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
            peers[msg['id']] = {
                'name': msg['name'],
                'addr': addr,
                'port': msg['port'],
                'last_seen': time.time(),
            }

def scan_for_dms():
    '''
    Listens for direct messages from peers.
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', CHAT_PORT))
    while True:
        data, addr = sock.recvfrom(1024)
        msg = decode_msg(data)
        if msg['type'] == 'msg':
            print(f'{peers.get(msg['from'], {'name': 'Unknown'})['name']} -> {NAME}: {msg['text']}')

def announcer():
    '''
    Periodically announces presence to other peers over the local network.
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = encode_msg({
        'id': ID,
        'type': 'announce',
        'name': NAME,
        'port': CHAT_PORT,
    })
    while True:
        sock.sendto(msg, ('<broadcast>', BROADCAST_PORT))
        time.sleep(2)

def send_message(id, text):
    if id not in peers:
        print('Unknown peer ID')
        return
    peer = peers[id]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_msg({
        'type': 'msg',
        'from': ID,
        'text': text,
    })
    sock.sendto(msg, (peer['addr'][0], peer['port']))
    print(f'{NAME} -> {peer['name']}: {text}')
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # msg = json.dumps({'type': 'msg', 'from': NAME, 'text': text}).encode()
    # # sock.sendto(msg, peer['addr'])
    # sock.sendto(msg, ('<broadcast>', BROADCAST_PORT))
    # print(f'To {peer['name']}: {text}')

# start threads
threading.Thread(target=scan_for_peers, daemon=True).start()
threading.Thread(target=scan_for_dms, daemon=True).start()
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
            print(f'{info['name']} ({id}) last seen {time.time() - info['last_seen']:.1f}s ago')
    elif parts[0] == 'msg' and len(parts) == 3:
        send_message(parts[1], parts[2])
    else:
        print('Unknown command')
