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

def decode_msg(data):
    return json.loads(data.decode())

def encode_msg(msg) -> bytes:
    return json.dumps(msg).encode()

class Me:
    '''
    Handles a connection to the local network.
    '''
    def __init__(self, name: str):
        self.name = name

        self.known_peers = {}

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
        Listens for direct messages from peers and prints them to the console.
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', CHAT_PORT))
        while True:
            data, addr = sock.recvfrom(1024)
            msg = decode_msg(data)
            if msg['type'] == 'msg':
                print(f'{self.known_peers.get(msg['from'], {'name': 'Unknown'})['name']} -> {self.name}: {msg['text']}')

    def announcer(self):
        '''
        Periodically announces presence to other peers over the local network.
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = encode_msg({
            'id': ID,
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
            'from': ID,
            'text': text,
        })
        sock.sendto(msg, (peer['addr'][0], peer['port']))
        print(f'{self.name} -> {peer['name']}: {text}')

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
                    print(f'{info['name']} ({id}) last seen {time.time() - info['last_seen']:.1f}s ago')
            elif parts[0] == 'msg' and len(parts) == 3:
                self.send_message(parts[1], parts[2])
            else:
                print('Unknown command')

if __name__ == '__main__':
    me = Me(NAME)
    me.start()
