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

waiting_for_ack = threading.Event()

class Me:
    '''
    Handles a connection to the local network.
    '''
    def __init__(self, name: str):
        self.name = name

        self.known_peers = {}

        self.timeout_ack_thread = threading.Thread(target=self.timeout_ack, daemon=True)
        self.scan_for_peers_thread = threading.Thread(target=self.scan_for_peers, daemon=True)
        self.scan_for_dms_thread = threading.Thread(target=self.scan_for_dms, daemon=True)
        self.announcer_thread = threading.Thread(target=self.announcer, daemon=True)

    def update_peer(self, id, info):
        '''
        Updates the known peers list with information about a peer, creating a
        new peer object if necessary.
        '''
        if id not in self.known_peers:
            self.known_peers[id] = {}
        self.known_peers[id].update(info)

    def should_stop_timeout_ack(self):
        '''
        Returns true if there are no expected acks from any peers.
        '''
        return not self.known_peers or not any('expected_ack' in p for p in self.known_peers.values())

    def timeout_ack(self):
        '''
        Waits for an ack using exponential backoff.
        '''
        while True:
            waiting_for_ack.wait()
            for id, peer in self.known_peers.items():
                if 'expected_ack' not in peer:
                    continue
                ack = peer['expected_ack']
                if time.time() > ack['latest_by']:
                    if ack['attempt'] >= 5:
                        print('No ACK received after 5 attempts, removing peer')
                        del self.known_peers[id]
                        if self.should_stop_timeout_ack():
                            waiting_for_ack.clear()
                        break

                    # update ack info
                    ack['attempt'] += 1
                    ack['latest_by'] = time.time() + (0.05 * (2 ** ack['attempt']))

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
                self.update_peer(msg['id'], {
                    'seq': self.known_peers.get(msg['id'], {}).get('seq', 0),
                    'name': msg['name'],
                    'addr': addr,
                    'port': msg['port'],
                    'last_seen': time.time(),
                })

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
            if msg['type'] == 'ack':
                peer = self.known_peers[msg['from']]
                if 'expected_ack' in peer and peer['expected_ack']['seq'] == msg['seq']:
                    del peer['expected_ack']
                    if self.should_stop_timeout_ack():
                        waiting_for_ack.clear()
                    print('ACK received from', msg['from'], 'for seq', msg['seq'])
                else:
                    print('ACK received from', msg['from'], 'for unknown seq', msg['seq'], '(maybe sent late?)')

            if msg['type'] == 'msg':
                # acknowledge receipt
                if msg['from'] in self.known_peers:
                    peer = self.known_peers[msg['from']]
                    peer_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    peer_sock.sendto(encode_msg({
                        'type': 'ack',
                        'from': ID,
                        'seq': msg['seq'],
                    }), (peer['addr'][0], peer['port']))

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
            'seq': peer['seq'],
            'type': 'msg',
            'from': ID,
            'text': text,
        })
        self.update_peer(id, {
            'seq': peer['seq'] + 1,
            'expected_ack': {
                'seq': peer['seq'],
                'attempt': 0,
                'latest_by': time.time() + 0.05 # 50 ms to ack, doubles each retry
            },
        })
        sock.sendto(msg, (peer['addr'][0], peer['port']))
        waiting_for_ack.set()

        peer_name = peer['name']
        print(f'{self.name} -> {peer_name}: {text}')

    def start(self):
        '''
        Starts the connection threads and enters the command loop.
        '''
        self.timeout_ack_thread.start()
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

if __name__ == '__main__':
    me = Me(NAME)
    me.start()
