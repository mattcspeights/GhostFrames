from scapy.all import sniff, Dot11, Raw
from payload_utils import parse_payload
from crypto_utils import decrypt_data
import time

def main():
    iface = "wlan1mon"
    expected_frames = 1000
    
    received_frames = {}  # msg_id -> (seq, decrypted_data)
    start_time = None
    last_frame_time = None
    
    print(f"[*] Starting to sniff for {expected_frames} frames on {iface}...")
    print("[*] Waiting for frames...\n")
    
    def packet_handler(pkt):
        nonlocal start_time, last_frame_time
        
        if pkt.haslayer(Dot11) and pkt.haslayer(Raw):
            try:
                raw_data = bytes(pkt[Raw].load)
                
                # Try to parse the payload
                parsed = parse_payload(raw_data)
                if parsed:
                    msg_type, msg_id, seq, encrypted_data = parsed
                    
                    if start_time is None:
                        start_time = time.time()
                    
                    last_frame_time = time.time()
                    
                    # Try to decrypt the data
                    try:
                        decrypted = decrypt_data(encrypted_data) if encrypted_data else ""
                    except:
                        decrypted = "[decrypt failed]"
                    
                    if msg_id not in received_frames:
                        received_frames[msg_id] = (seq, decrypted)
                        
                        if len(received_frames) % 100 == 0:
                            print(f"[*] Received {len(received_frames)}/{expected_frames} frames")
                        
                        # Stop after receiving expected number of frames
                        if len(received_frames) >= expected_frames:
                            return True  # Stop sniffing
            except Exception as e:
                pass
    
    # Sniff with a timeout to avoid hanging forever
    try:
        sniff(iface=iface, prn=packet_handler, store=0, timeout=120, stop_filter=lambda x: packet_handler(x))
    except KeyboardInterrupt:
        print("\n[*] Sniffing interrupted by user")
    
    # Wait a bit more for any late frames
    print("\n[*] Waiting 5 more seconds for late frames...")
    time.sleep(5)
    
    # Calculate statistics
    end_time = time.time()
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print(f"Expected frames: {expected_frames}")
    print(f"Received frames: {len(received_frames)}")
    print(f"Dropped frames: {expected_frames - len(received_frames)}")
    print(f"Success rate: {(len(received_frames)/expected_frames)*100:.2f}%")
    print(f"Drop rate: {((expected_frames - len(received_frames))/expected_frames)*100:.2f}%")
    
    if start_time and last_frame_time:
        duration = last_frame_time - start_time
        print(f"Duration: {duration:.2f} seconds")
        print(f"Average rate: {len(received_frames)/duration:.2f} frames/sec")
    
    # Show which frames were dropped (if not too many)
    if len(received_frames) < expected_frames:
        missing = sorted(set(range(1, expected_frames + 1)) - received_frames.keys())
        if len(missing) <= 50:
            print(f"\nMissing frame IDs: {missing}")
        else:
            print(f"\nFirst 50 missing frames: {missing[:50]}")
            print(f"Last 50 missing frames: {missing[-50:]}")
    
    # Show sample of received frames
    if received_frames:
        print(f"\nSample received frames:")
        sample_ids = sorted(received_frames.keys())[:5]
        for msg_id in sample_ids:
            seq, data = received_frames[msg_id]
            print(f"  Frame {msg_id}: seq={seq}, data='{data}'")
    
    print("="*60)

if __name__ == "__main__":
    main()