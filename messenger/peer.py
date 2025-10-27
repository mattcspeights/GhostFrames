import json
import random
import time
import threading
from send_frame import send_frame
from sniff_frames import sniff_frames
from enums import MsgType
from payload_utils import parse_payload, get_mac
from scapy.all import sniff, Dot11, Raw

IFACE = "wlan1mon"
SRC_MAC = get_mac(IFACE)
BROADCAST_MAC = "ff:ff:ff:ff:ff:ff" # initialize to default for discovery

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
    def __init__(self, id: str, name: str, debug_mode: bool = False):
        self.id = id
        self.name = name
        self.debug_mode = debug_mode

        self.known_peers = {}
        self.message_listeners = []

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

    def register_message_listener(self, callback):
        '''
        Registers a callback to be called when a message from a peer is
        received.
        '''
        self.message_listeners.append(callback)

    def remove_message_listener(self, callback):
        '''
        Removes a previously registered message listener.
        '''
        self.message_listeners.remove(callback)

    def frame_listener(self):
        '''
        Listens for all frame types and handles them appropriately.
        '''
        def handler(pkt):
            if pkt.haslayer(Dot11):
                dot11 = pkt[Dot11]
                # Only process our frames with the right pseudo-BSSID
                if dot11.addr3 == "02:07:08:15:19:20" and pkt.haslayer(Raw):
                    payload = pkt[Raw].load
                    parsed = parse_payload(payload)
                    if parsed:
                        msg_type, msg_id, seq, data = parsed
                        sender_mac = dot11.addr2
                        
                        if self.debug_mode:
                            print(f"[+] Received frame: Type={msg_type.name}, ID={msg_id}, Seq={seq}, From={sender_mac}, Data='{data}'")
                        
                        # Skip our own frames
                        if sender_mac == SRC_MAC:
                            if self.debug_mode:
                                print(f"[*] Ignoring own frame")
                            return
                        
                        if msg_type == MsgType.HANDSHAKE_REQ:
                            # Parse handshake request: "port|name" format
                            parts = data.split('|')
                            if len(parts) >= 2:
                                peer_id = parts[1]  # Use name as ID for now
                                if peer_id != id:
                                    self.update_peer(peer_id, {
                                        'seq': self.known_peers.get(peer_id, {}).get('seq', 0),
                                        'name': peer_id,
                                        'mac': sender_mac,  # Source MAC
                                        'last_seen': time.time(),
                                    })
                                    # Send handshake acknowledgment
                                    ack_data = f"0|{self.name}"  # port not used, just name
                                    send_frame(MsgType.HANDSHAKE_ACK, get_next_msg_id(), 0, 
                                             ack_data, IFACE, sender_mac, SRC_MAC, self.debug_mode)

                        elif msg_type == MsgType.HANDSHAKE_ACK:
                            # Parse handshake ack: "port|name" format
                            parts = data.split('|')
                            if len(parts) >= 2:
                                peer_id = parts[1]
                                if peer_id != id:
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
                                # TODO: This should be a temporary solution but it's the easiest I could think of for now
                                time.sleep(0.001)
                                
                                # Send acknowledgment
                                ack_data = f"{msg_id}|{seq}"
                                send_frame(MsgType.MSG_ACK, get_next_msg_id(), 0, 
                                         ack_data, IFACE, sender_mac, SRC_MAC, self.debug_mode)
                                
                                sender_name = self.known_peers.get(sender_id, {'name': 'Unknown'})['name']
                                print(f'{sender_name} -> {self.name}: {data}')

                                # Notify listeners
                                for callback in self.message_listeners:
                                    callback(sender_id, data)
                    else:
                        if self.debug_mode:
                            print(f"[!] Received unparseable frame payload: {payload!r}")

        sniff(iface=IFACE, prn=handler, store=0)

    def announcer(self):
        '''
        Periodically announces presence to other peers over the local network.
        '''
        while True:
            # Send handshake request as announcement: "port|name" format
            announce_data = f"0|{self.name}"  # port not used, just name
            send_frame(MsgType.HANDSHAKE_REQ, get_next_msg_id(), 0, 
                     announce_data, IFACE, BROADCAST_MAC, SRC_MAC, self.debug_mode)
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
                 text, IFACE, peer['mac'], SRC_MAC, self.debug_mode)
        
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
        Starts the connection threads.
        '''
        self.timeout_ack_thread.start()
        self.frame_listener_thread.start()
        self.announcer_thread.start()

    def cmd(self):
        '''
        Enters cmd mode where you can interact with the messenger from the
        command line.
        '''
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
    name = input('What\'s your name? ')
    debug_mode = input('Enable debug mode to show all frames sent and received (y/n):').startswith('y')
    id = f'{name}' # TODO: make unique

    me = Me(id, name, debug_mode)
    me.start()
    me.cmd()
