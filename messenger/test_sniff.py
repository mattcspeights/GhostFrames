from scapy.all import sniff, Dot11
import time

def main():
    iface = "wlan1mon"
    filter_substring = b"GF|"
    expected_frames = 1000
    
    received_frames = set()
    start_time = None
    last_frame_time = None
    
    print(f"[*] Starting to sniff for {expected_frames} frames on {iface}...")
    print(f"[*] Filtering for frames containing: {filter_substring}")
    print("[*] Waiting for frames...\n")
    
    def packet_handler(pkt):
        nonlocal start_time, last_frame_time
        
        if pkt.haslayer(Dot11):
            try:
                raw_data = bytes(pkt)
                if filter_substring in raw_data:
                    if start_time is None:
                        start_time = time.time()
                    
                    last_frame_time = time.time()
                    
                    # Extract frame number from the data
                    # Looking for pattern like "Frame X" in the payload
                    idx = raw_data.find(b"Frame ")
                    if idx != -1:
                        # Extract the frame number
                        frame_str = raw_data[idx:idx+20].decode('utf-8', errors='ignore')
                        try:
                            frame_num = int(frame_str.split()[1].split('\x00')[0])
                            if frame_num not in received_frames:
                                received_frames.add(frame_num)
                                
                                if len(received_frames) % 100 == 0:
                                    print(f"[*] Received {len(received_frames)}/{expected_frames} frames")
                                
                                # Stop after receiving expected number of frames or timeout
                                if len(received_frames) >= expected_frames:
                                    return True  # Stop sniffing
                        except (ValueError, IndexError):
                            pass
            except Exception as e:
                pass
    
    # Sniff with a timeout to avoid hanging forever
    try:
        sniff(iface=iface, prn=packet_handler, store=0, timeout=30, stop_filter=lambda x: packet_handler(x))
    except KeyboardInterrupt:
        print("\n[*] Sniffing interrupted by user")
    
    # Wait a bit more for any late frames
    print("\n[*] Waiting 2 more seconds for late frames...")
    time.sleep(2)
    
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
        missing = sorted(set(range(1, expected_frames + 1)) - received_frames)
        if len(missing) <= 50:
            print(f"\nMissing frame numbers: {missing}")
        else:
            print(f"\nFirst 50 missing frames: {missing[:50]}")
    
    print("="*60)

if __name__ == "__main__":
    main()