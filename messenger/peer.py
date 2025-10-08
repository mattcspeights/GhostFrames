import json
import random
import time
import threading
from datetime import datetime
from send_frame import send_frame
from sniff_frames import sniff_frames
from enums import MsgType
from payload_utils import parse_payload, get_mac
from scapy.all import Dot11, Raw

IFACE = "wlan1mon"
SRC_MAC = get_mac(IFACE)
BROADCAST_MAC = "ff:ff:ff:ff:ff:ff" # initialize to default for discovery

NAME = input('What\'s your name? ')
DEBUG_MODE = input('Enable debug mode to show all frames sent and received (y/n):').startswith('y')
ID = f'{NAME}' # TODO: make unique

waiting_for_ack = threading.Event()
msg_id_counter = 0

def get_next_msg_id():
    global msg_id_counter
    msg_id_counter += 1
    return msg_id_counter

class Me:
    '''
    Handles a connection to the local network.
    '''
    def __init__(self, name: str):
        self.name = name

        self.known_peers = {}

        self.timeout_ack_thread = threading.Thread(target=self.timeout_ack, daemon=True)
        self.frame_listener_thread = threading.Thread(target=self.frame_listener, daemon=True)
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

    def handle_frame(self, pkt, msg_type, msg_id, seq, data):
        '''
        Handle received frames based on type.
        '''
        dot11 = pkt[Dot11]
        sender_mac = dot11.addr2
        
        if DEBUG_MODE:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] Received frame: Type={msg_type.name}, ID={msg_id}, Seq={seq}, From={sender_mac}, Data='{data}'")
        
        # Skip our own frames
        if sender_mac == SRC_MAC:
            if DEBUG_MODE:
                print(f"[*] Ignoring own frame")
            return
        
        if msg_type == MsgType.HANDSHAKE_REQ:
            # Parse handshake request: "port|name" format
            parts = data.split('|')
            if len(parts) >= 2:
                peer_id = parts[1]  # Use name as ID for now
                if peer_id != ID:  # Don't add ourselves
                    self.update_peer(peer_id, {
                        'seq': self.known_peers.get(peer_id, {}).get('seq', 0),
                        'name': peer_id,
                        'mac': sender_mac,  # Source MAC
                        'last_seen': time.time(),
                    })
                    # Send handshake acknowledgment
                    ack_data = f"0|{self.name}"  # port not used, just name
                    send_frame(MsgType.HANDSHAKE_ACK, get_next_msg_id(), 0, 
                             ack_data, IFACE, sender_mac, SRC_MAC, DEBUG_MODE)

        elif msg_type == MsgType.HANDSHAKE_ACK:
            # Parse handshake ack: "port|name" format
            parts = data.split('|')
            if len(parts) >= 2:
                peer_id = parts[1]
                if peer_id != ID:
                    self.update_peer(peer_id, {
                        'seq': self.known_peers.get(peer_id, {}).get('seq', 0),
                        'name': peer_id,
                        'mac': sender_mac,
                        'last_seen': time.time(),
                    })

        elif msg_type == MsgType.MSG_ACK:
            # Parse ACK: "msg_id|seq" format
            parts = data.split('|')
            if len(parts) >= 2:
                ack_msg_id = int(parts[0])
                ack_seq = int(parts[1])
                
                # Find peer by MAC address
                peer_id = None
                for pid, pinfo in self.known_peers.items():
                    if pinfo.get('mac') == sender_mac:
                        peer_id = pid
                        break
                
                if peer_id and peer_id in self.known_peers:
                    peer = self.known_peers[peer_id]
                    if 'expected_ack' in peer and peer['expected_ack']['seq'] == ack_seq:
                        del peer['expected_ack']
                        if self.should_stop_timeout_ack():
                            waiting_for_ack.clear()
                        print('ACK received from', peer_id, 'for seq', ack_seq)
                    else:
                        print('ACK received from', peer_id, 'for unknown seq', ack_seq, '(maybe sent late?)')

        elif msg_type == MsgType.MSG:
            # Find sender by MAC address
            sender_id = None
            for pid, pinfo in self.known_peers.items():
                if pinfo.get('mac') == sender_mac:
                    sender_id = pid
                    break
            
            if sender_id:
                # Small delay to make sure sender has updated state
                time.sleep(0.001)  # 1ms delay
                
                # Send acknowledgment
                ack_data = f"{msg_id}|{seq}"
                send_frame(MsgType.MSG_ACK, get_next_msg_id(), 0, 
                         ack_data, IFACE, sender_mac, SRC_MAC, DEBUG_MODE)
                
                sender_name = self.known_peers.get(sender_id, {'name': 'Unknown'})['name']
                print(f'{sender_name} -> {self.name}: {data}')

    def frame_listener(self):
        '''
        Listens for all frame types and handles them appropriately.
        '''
        sniff_frames(IFACE, filter_substring=b"GF|", debug=DEBUG_MODE, callback=self.handle_frame)

    def announcer(self):
        '''
        Periodically announces presence to other peers over the local network.
        '''
        while True:
            # Send handshake request as announcement: "port|name" format
            announce_data = f"0|{self.name}"  # port not used, just name
            send_frame(MsgType.HANDSHAKE_REQ, get_next_msg_id(), 0, 
                     announce_data, IFACE, BROADCAST_MAC, SRC_MAC, DEBUG_MODE)
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
        if 'mac' not in peer:
            print('Peer MAC address not known')
            return

        # Send message frame
        send_frame(MsgType.MSG, get_next_msg_id(), peer['seq'], 
                 text, IFACE, peer['mac'], SRC_MAC, DEBUG_MODE)
        
        self.update_peer(id, {
            'seq': peer['seq'] + 1,
            'expected_ack': {
                'seq': peer['seq'],
                'attempt': 0,
                'latest_by': time.time() + 0.05 # 50 ms to ack, doubles each retry
            },
        })
        waiting_for_ack.set()

        peer_name = peer['name']
        print(f'{self.name} -> {peer_name}: {text}')

    def start(self):
        '''
        Starts the connection threads and enters the command loop.
        '''
        self.timeout_ack_thread.start()
        self.frame_listener_thread.start()
        self.announcer_thread.start()

        print("Commands:")
        print("  ls                 = list known peers")
        print("  msg <id> <message> = send message to peer")

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