import json
import random
import time
import threading
import os
import base64
from send_frame import send_frame
from sniff_frames import sniff_frames
from enums import MsgType
from payload_utils import parse_payload, get_mac
from scapy.all import sniff, Dot11, Raw

CHUNK_SIZE = 1000 # typically 1500 bytes MTU data, leave some room in case

IFACE = "wlan1mon"
SRC_MAC = get_mac(IFACE)
BROADCAST_MAC = "ff:ff:ff:ff:ff:ff" # initialize to default for discovery

waiting_for_ack = threading.Event()

class Me:
    '''
    Handles a connection to the local network.
    '''
    def __init__(self, name: str, debug_mode: bool = False):
        self.id = name
        self.name = name
        self.debug_mode = debug_mode

        self.msg_id_counter = 1

        self.known_peers = {}
        self.received_messages = {}  # Track (sender_mac, msg_id, seq) to prevent duplicates
        self.file_transfers = {}  # Track ongoing file transfers: {(sender_mac, msg_id): {filename, size, chunks, received_seqs}}

        self.message_listeners = []

        self.timeout_ack_thread = threading.Thread(target=self.timeout_ack, daemon=True)
        self.frame_listener_thread = threading.Thread(target=self.frame_listener, daemon=True)
        self.announcer_thread = threading.Thread(target=self.announcer, daemon=True)

    def get_next_msg_id(self):
        '''
        Returns the next message ID and increments the counter.
        '''
        current_id = self.msg_id_counter
        self.msg_id_counter += 1
        return current_id

    def update_peer(self, id, info):
        '''
        Updates the known peers list with information about a peer, creating a
        new peer object if necessary.
        '''
        is_new_peer = id not in self.known_peers
        if is_new_peer:
            self.known_peers[id] = {}
        
        self.known_peers[id].update(info)
        
        # Print message when a new peer is added
        if is_new_peer and 'name' in info:
            print(f'{info["name"]} has joined the network')

    def should_stop_timeout_ack(self):
        '''
        Returns true if there are no expected acks from any peers.
        '''
        return not self.known_peers or not any('expected_ack' in p for p in self.known_peers.values())

    def cleanup_old_messages(self):
        '''
        Remove received message entries older than 90 seconds to prevent memory growth.
        '''
        current_time = time.time()
        cutoff_time = current_time - 90  # 90 seconds
        
        # Create a new dict with only recent messages
        self.received_messages = {
            key: timestamp for key, timestamp in self.received_messages.items()
            if timestamp > cutoff_time
        }

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
                        # Check if peer ID is still in known peers
                        if id in self.known_peers:
                            if ack.get('type') == 'file':
                                print(f'File transfer failed: No ACK received after 5 attempts from {id}')
                                # Don't remove peer for file transfer failures, just clear the expected ACK
                                del self.known_peers[id]['expected_ack']
                            else:
                                print('No ACK received after 5 attempts, removing peer')
                                del self.known_peers[id]
                            
                            if self.should_stop_timeout_ack():
                                waiting_for_ack.clear()
                        break

                    ack['attempt'] += 1
                    if ack.get('type') == 'file':
                        # Longer timeout for file transfers (starts at 500ms, doubles each retry)
                        ack['latest_by'] = time.time() + (0.5 * (2 ** ack['attempt']))
                    else:
                        # Regular message timeout (starts at 50ms, doubles each retry)
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
                            # Check for duplicate handshake requests
                            message_key = (sender_mac, msg_id, seq)
                            if message_key in self.received_messages:
                                if self.debug_mode:
                                    print(f"[*] Ignoring duplicate handshake request: ID={msg_id}, Seq={seq} from {sender_mac}")
                                return
                            
                            # Record this handshake as received
                            self.received_messages[message_key] = time.time()
                            
                            # Parse handshake request: "port|name" format
                            parts = data.split('|')
                            if len(parts) >= 2:
                                peer_id = parts[1]  # Use name as ID for now
                                if peer_id != id:  # Don't add ourselves
                                    # Check if this is a new peer
                                    is_new_peer = peer_id not in self.known_peers
                                    self.update_peer(peer_id, {
                                        'name': peer_id,
                                        'mac': sender_mac,  # Source MAC
                                        'last_seen': time.time(),
                                    })
                                    
                                    # Send handshake acknowledgment
                                    ack_data = f"0|{self.name}"  # port not used, just name
                                    send_frame(MsgType.HANDSHAKE_ACK, self.get_next_msg_id(), 0, 
                                             ack_data, IFACE, sender_mac, SRC_MAC, self.debug_mode)

                                    # If this is a new peer, also send a handshake request back for mutual discovery
                                    if is_new_peer:
                                        req_data = f"0|{self.name}"  # port not used, just name
                                        send_frame(MsgType.HANDSHAKE_REQ, self.get_next_msg_id(), 0, 
                                                 req_data, IFACE, sender_mac, SRC_MAC, self.debug_mode)

                        elif msg_type == MsgType.HANDSHAKE_ACK:
                            # Check for duplicate handshake acks
                            message_key = (sender_mac, msg_id, seq)
                            if message_key in self.received_messages:
                                if self.debug_mode:
                                    print(f"[*] Ignoring duplicate handshake ack: ID={msg_id}, Seq={seq} from {sender_mac}")
                                return
                            
                            # Record this handshake ack as received
                            self.received_messages[message_key] = time.time()
                            
                            # Parse handshake ack: "port|name" format
                            parts = data.split('|')
                            if len(parts) >= 2:
                                peer_id = parts[1]
                                if peer_id != id:
                                    self.update_peer(peer_id, {
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
                                    if 'expected_ack' in peer and peer['expected_ack']['msg_id'] == ack_msg_id:
                                        del peer['expected_ack']
                                        if self.should_stop_timeout_ack():
                                            waiting_for_ack.clear()
                                        print('ACK received from', peer_id, 'for msg_id', ack_msg_id)
                                    else:
                                        print('ACK received from', peer_id, 'for unknown msg_id', ack_msg_id, '(maybe sent late?)')

                        elif msg_type == MsgType.RENAME:
                            # Find sender by MAC address
                            sender_id = None
                            for pid, pinfo in self.known_peers.items():
                                if pinfo.get('mac') == sender_mac:
                                    sender_id = pid
                                    break

                            if sender_id and sender_id in self.known_peers:
                                old_name = self.known_peers[sender_id]['name']
                                self.known_peers[sender_id]['name'] = data
                                print(f'{old_name} has renamed to {data}')

                                # TODO temp: also change the peer ID to the new name
                                self.known_peers[data] = self.known_peers.pop(sender_id)

                                # Send RENAME_ACK
                                send_frame(MsgType.RENAME_ACK, self.get_next_msg_id(), 0, 
                                         "", IFACE, sender_mac, SRC_MAC, self.debug_mode)

                        elif msg_type == MsgType.RENAME_ACK:
                            # No action needed for RENAME_ACK currently
                            pass

                        elif msg_type == MsgType.TERMINATE:
                            # Find sender by MAC address and remove from peers
                            sender_id = None
                            for pid, pinfo in self.known_peers.items():
                                if pinfo.get('mac') == sender_mac:
                                    sender_id = pid
                                    break
                            
                            if sender_id and sender_id in self.known_peers:
                                sender_name = self.known_peers[sender_id]['name']
                                del self.known_peers[sender_id]
                                print(f'{sender_name} has left the network')

                        elif msg_type == MsgType.HEARTBEAT:
                            # Update last_seen for known peers on heartbeat
                            for pid, pinfo in self.known_peers.items():
                                if pinfo.get('mac') == sender_mac:
                                    pinfo['last_seen'] = time.time()
                                    if self.debug_mode:
                                        print(f"[*] Heartbeat from {pinfo['name']}")
                                    break

                        elif msg_type == MsgType.MSG:
                            # Check for duplicate messages
                            message_key = (sender_mac, msg_id, seq)
                            if message_key in self.received_messages:
                                if self.debug_mode:
                                    print(f"[*] Ignoring duplicate message: ID={msg_id}, Seq={seq} from {sender_mac}")
                                return
                            
                            # Record this message as received
                            self.received_messages[message_key] = time.time()
                            
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
                                send_frame(MsgType.MSG_ACK, self.get_next_msg_id(), 0, 
                                         ack_data, IFACE, sender_mac, SRC_MAC, self.debug_mode)
                                
                                sender_name = self.known_peers.get(sender_id, {'name': 'Unknown'})['name']
                                print(f'{sender_name} -> {self.name}: {data}')

                                # Notify listeners
                                for callback in self.message_listeners:
                                    callback(sender_id, data)
                            
                            # Periodically clean up old message records
                            if len(self.received_messages) > 100:  # Clean up when we have many entries
                                self.cleanup_old_messages()

                        elif msg_type == MsgType.FILE_INIT:
                            # Check for duplicate file init
                            message_key = (sender_mac, msg_id, seq)
                            if message_key in self.received_messages:
                                if self.debug_mode:
                                    print(f"[*] Ignoring duplicate file init: ID={msg_id}, Seq={seq} from {sender_mac}")
                                return
                            
                            # Record this file init as received
                            self.received_messages[message_key] = time.time()
                            
                            # Parse file init: "filename|size" format
                            parts = data.split('|')
                            if len(parts) >= 2:
                                filename = parts[0]
                                file_size = int(parts[1])
                                
                                # Initialize file transfer tracking
                                transfer_key = (sender_mac, msg_id)
                                self.file_transfers[transfer_key] = {
                                    'filename': filename,
                                    'size': file_size,
                                    'chunks': {},
                                    'received_seqs': set()
                                }
                                
                                # Find sender name
                                sender_name = "Unknown"
                                for pid, pinfo in self.known_peers.items():
                                    if pinfo.get('mac') == sender_mac:
                                        sender_name = pinfo['name']
                                        break
                                
                                print(f'Receiving file {filename} ({file_size} bytes) from {sender_name}...')

                        elif msg_type == MsgType.FILE_CHUNK:
                            # Check for duplicate file chunk
                            message_key = (sender_mac, msg_id, seq)
                            if message_key in self.received_messages:
                                if self.debug_mode:
                                    print(f"[*] Ignoring duplicate file chunk: ID={msg_id}, Seq={seq} from {sender_mac}")
                                return
                            
                            # Record this file chunk as received
                            self.received_messages[message_key] = time.time()
                            
                            # Store chunk data
                            transfer_key = (sender_mac, msg_id)
                            if transfer_key in self.file_transfers:
                                transfer = self.file_transfers[transfer_key]
                                # Decode base64 chunk data
                                try:
                                    chunk_data = base64.b64decode(data.encode('ascii'))
                                    transfer['chunks'][seq] = chunk_data
                                    transfer['received_seqs'].add(seq)
                                    
                                    if self.debug_mode:
                                        print(f"[*] Received file chunk {seq} ({len(chunk_data)} bytes)")
                                except Exception as e:
                                    print(f"Error decoding file chunk: {e}")

                        elif msg_type == MsgType.FILE_END:
                            # Check for duplicate file end
                            message_key = (sender_mac, msg_id, seq)
                            if message_key in self.received_messages:
                                if self.debug_mode:
                                    print(f"[*] Ignoring duplicate file end: ID={msg_id}, Seq={seq} from {sender_mac}")
                                return
                            
                            # Record this file end as received
                            self.received_messages[message_key] = time.time()
                            
                            # Finalize file transfer
                            transfer_key = (sender_mac, msg_id)
                            if transfer_key in self.file_transfers:
                                transfer = self.file_transfers[transfer_key]
                                transfer['received_seqs'].add(seq)  # Add FILE_END seq
                                
                                # Send FILE_ACK with received sequence numbers
                                received_seqs_str = ','.join(map(str, sorted(transfer['received_seqs'])))
                                ack_data = f"{msg_id}|{received_seqs_str}"
                                send_frame(MsgType.FILE_ACK, self.get_next_msg_id(), 0, 
                                         ack_data, IFACE, sender_mac, SRC_MAC, self.debug_mode)
                                
                                # Reassemble and save file
                                self.reassemble_file(transfer_key)

                        elif msg_type == MsgType.FILE_ACK:
                            # Parse FILE_ACK: "msg_id|seq1,seq2,seq3..." format
                            parts = data.split('|')
                            if len(parts) >= 2:
                                ack_msg_id = int(parts[0])
                                received_seqs = set(map(int, parts[1].split(','))) if parts[1] else set()
                                
                                # Find peer by MAC address
                                peer_id = None
                                for pid, pinfo in self.known_peers.items():
                                    if pinfo.get('mac') == sender_mac:
                                        peer_id = pid
                                        break
                                
                                if peer_id and peer_id in self.known_peers:
                                    peer = self.known_peers[peer_id]
                                    peer_name = peer['name']
                                    
                                    # Clear expected ACK if this matches
                                    if 'expected_ack' in peer and peer['expected_ack']['msg_id'] == ack_msg_id:
                                        del peer['expected_ack']
                                        if self.should_stop_timeout_ack():
                                            waiting_for_ack.clear()
                                        print(f'File transfer completed! ACK received from {peer_name}: {len(received_seqs)} chunks for msg_id {ack_msg_id}')
                                    else:
                                        print(f'File transfer ACK from {peer_name}: received {len(received_seqs)} chunks for msg_id {ack_msg_id} (maybe sent late?)')
                    else:
                        if self.debug_mode:
                            print(f"[!] Received unparseable frame payload: {payload!r}")

        sniff(iface=IFACE, prn=handler, store=0)

    def announcer(self):
        '''
        Sends initial handshake request and then periodic heartbeats to announce presence.
        '''
        # Send initial handshake request on startup
        announce_data = f"0|{self.name}"  # port not used, just name
        send_frame(MsgType.HANDSHAKE_REQ, self.get_next_msg_id(), 0, 
                 announce_data, IFACE, BROADCAST_MAC, SRC_MAC, self.debug_mode)
        
        # Then send heartbeats every 5 seconds
        while True:
            time.sleep(5)
            send_frame(MsgType.HEARTBEAT, self.get_next_msg_id(), 0, 
                     "", IFACE, BROADCAST_MAC, SRC_MAC, self.debug_mode)

    def rename(self, new_name):
        '''
        Renames this peer to the given name, and announces the change to known
        peers.
        '''
        self.id = new_name
        self.name = new_name
        send_frame(MsgType.RENAME, self.get_next_msg_id(), 0, 
                 new_name, IFACE, BROADCAST_MAC, SRC_MAC, self.debug_mode)

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

        # Send message frame with seq=1 (messages are not chunked)
        msg_id = self.get_next_msg_id()
        send_frame(MsgType.MSG, msg_id, 1, 
                 text, IFACE, peer['mac'], SRC_MAC, self.debug_mode)
        
        self.update_peer(id, {
            'expected_ack': {
                'msg_id': msg_id,
                'attempt': 0,
                'latest_by': time.time() + 0.05 # 50 ms to ack, doubles each retry
            },
        })
        waiting_for_ack.set()

        peer_name = peer['name']
        print(f'{self.name} -> {peer_name}: {text}')

    def send_file(self, peer_id, file_path):
        '''
        Sends a file to a known peer by breaking it into chunks.
        '''
        if peer_id not in self.known_peers:
            print('Unknown peer ID')
            return

        peer = self.known_peers[peer_id]
        if 'mac' not in peer:
            print('Peer MAC address not known')
            return

        if not os.path.exists(file_path):
            print(f'File not found: {file_path}')
            return

        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
        except Exception as e:
            print(f'Error reading file: {e}')
            return

        filename = os.path.basename(file_path)
        file_size = len(file_data)
        msg_id = self.get_next_msg_id()
        
        print(f'Sending file {filename} ({file_size} bytes) to {peer["name"]}...')

        # Send FILE_INIT
        init_data = f"{filename}|{file_size}"
        send_frame(MsgType.FILE_INIT, msg_id, 1, init_data, IFACE, peer['mac'], SRC_MAC, self.debug_mode)

        # Send FILE_CHUNK frames
        seq = 2  # Start from seq 2 (seq 1 was FILE_INIT)
        for i in range(0, file_size, CHUNK_SIZE):
            chunk = file_data[i:i + CHUNK_SIZE]
            # Encode chunk as base64 to handle binary data safely
            chunk_b64 = base64.b64encode(chunk).decode('ascii')
            send_frame(MsgType.FILE_CHUNK, msg_id, seq, chunk_b64, IFACE, peer['mac'], SRC_MAC, self.debug_mode)
            seq += 1

        # Send FILE_END
        send_frame(MsgType.FILE_END, msg_id, seq, "", IFACE, peer['mac'], SRC_MAC, self.debug_mode)
        
        # Set up expected FILE_ACK with timeout and retry logic
        self.update_peer(peer_id, {
            'expected_ack': {
                'msg_id': msg_id,
                'attempt': 0,
                'latest_by': time.time() + 0.5,  # 500ms for file transfer ACK (longer than regular messages)
                'type': 'file'  # Mark this as a file transfer ACK
            },
        })
        waiting_for_ack.set()
        
        print(f'File {filename} sent in {seq-1} chunks')

    def reassemble_file(self, transfer_key):
        '''
        Reassembles received file chunks and saves the file.
        '''
        if transfer_key not in self.file_transfers:
            return

        transfer = self.file_transfers[transfer_key]
        filename = transfer['filename']
        expected_size = transfer['size']
        chunks = transfer['chunks']

        # Sort chunks by sequence number and reassemble
        sorted_seqs = sorted(chunks.keys())
        file_data = b''
        
        for seq in sorted_seqs:
            file_data += chunks[seq]

        # Verify file size
        if len(file_data) != expected_size:
            print(f'Warning: File size mismatch for {filename}. Expected {expected_size}, got {len(file_data)}')

        # Save file with a prefix to avoid overwriting
        safe_filename = f"received_{filename}"
        counter = 1
        while os.path.exists(safe_filename):
            name, ext = os.path.splitext(filename)
            safe_filename = f"received_{name}_{counter}{ext}"
            counter += 1

        try:
            with open(safe_filename, 'wb') as f:
                f.write(file_data)
            
            # Find sender name
            sender_mac = transfer_key[0]
            sender_name = "Unknown"
            for pid, pinfo in self.known_peers.items():
                if pinfo.get('mac') == sender_mac:
                    sender_name = pinfo['name']
                    break
            
            print(f'File saved as {safe_filename} ({len(file_data)} bytes) from {sender_name}')
            
        except Exception as e:
            print(f'Error saving file {safe_filename}: {e}')

        # Clean up transfer tracking
        del self.file_transfers[transfer_key]

    def send_terminate(self):
        '''
        Sends a terminate frame to all known peers to notify them we're leaving.
        '''
        for id, peer in self.known_peers.items():
            if 'mac' in peer:
                send_frame(MsgType.TERMINATE, self.get_next_msg_id(), 1, 
                         "", IFACE, peer['mac'], SRC_MAC, self.debug_mode)
        print('Terminate frames sent to all peers')

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
ls                    = list known peers
msg <id> <message>    = send message to peer
file <id> <filepath>  = send file to peer
q                     = send terminate frame and quit''')

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
            elif parts[0] == 'file' and len(parts) == 3:
                self.send_file(parts[1], parts[2])
            elif parts[0] == 'q':
                self.send_terminate()
                break
            else:
                print('Unknown command')

if __name__ == '__main__':
    name = input('What\'s your name? ')
    debug_mode = input('Enable debug mode to show all frames sent and received (y/n):').startswith('y')
    id = f'{name}' # TODO: make unique

    me = Me(name, debug_mode)
    me.start()
    me.cmd()
