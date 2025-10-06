import json
import random
import socket
import time
import threading
from scapy.all import Dot11, Raw
from send_frame import send_frame
from sniff_frames import sniff_frames
from payload_utils import build_payload, parse_payload
from enums import MsgType

BROADCAST_PORT = 65432
CHAT_PORT = int(random.uniform(20000, 30000))
NAME = input('What\'s your name? ')
# ID = f'{NAME}-{int(time.time())}'
ID = f'{NAME}' # TODO: make unique

class Messenger:
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
        def handle_frame(pkt):
            if pkt.haslayer(Raw):
                payload = pkt[Raw].load
                msg = parse_payload(payload)
                if msg is not None:
                    msg_type, msg_id, seq, data = msg
                    if msg_type == MsgType.HANDSHAKE_REQ:
                        # Parse port|name from data
                        parts = data.split('|')
                        if len(parts) >= 2:
                            port, name = parts[0], parts[1]
                            peer_id = name  # Using name as ID for now
                            self.known_peers[peer_id] = {
                                'name': name,
                                'addr': pkt[Dot11].addr2,  # Source MAC address
                                'port': int(port),
                                'last_seen': time.time(),
                            }
        
        # Use sniff_frames with our handler
        from scapy.all import sniff, Dot11, Raw
        sniff(iface="wlan0", prn=handle_frame, store=0, filter="type mgt subtype beacon")

    def scan_for_dms(self):
        '''
        Listens for direct messages from peers and prints them to the console.
        '''
        def handle_dm_frame(pkt):
            if pkt.haslayer(Raw):
                payload = pkt[Raw].load
                msg = parse_payload(payload)
                if msg is not None:
                    msg_type, msg_id, seq, data = msg
                    if msg_type == MsgType.MSG:
                        # Find sender by MAC address
                        sender_addr = pkt[Dot11].addr2
                        sender_name = "Unknown"
                        for peer_id, peer_info in self.known_peers.items():
                            if peer_info['addr'] == sender_addr:
                                sender_name = peer_info['name']
                                break
                        content = data
                        print(f'{sender_name} -> {self.name}: {content}')
        
        # Listen for direct messages
        from scapy.all import sniff, Dot11, Raw
        sniff(iface="wlan0", prn=handle_dm_frame, store=0)

    def announcer(self):
        '''
        Periodically announces presence to other peers over the local network.
        '''
        while True:
            # Create handshake request with port|name format
            data = f"{CHAT_PORT}|{self.name}"
            send_frame(
                msg_type=MsgType.HANDSHAKE_REQ,
                msg_id=random.randint(1000, 9999),
                seq=1,
                data=data,
                iface="wlan0",
                dst="ff:ff:ff:ff:ff:ff", # for broadcast
                src="02:07:08:15:19:20" # pseudo-MAC
            )
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
        
        # Send message with MSG type
        send_frame(
            msg_type=MsgType.MSG,
            msg_id=random.randint(1000, 9999),
            seq=1,
            data=text,
            iface="wlan0",
            dst=peer['addr'],
            src="02:07:08:15:19:20" # pseudo-MAC
        )
        
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

if __name__ == '__main__':
    messenger = Messenger(NAME)
    messenger.start()
