from send_frame import send_frame
from enums import MsgType
import time

def main():
    iface = "wlan1mon"
    dst = "ff:ff:ff:ff:ff:ff"
    src = "aa:bb:cc:dd:ee:ff"

    total_frames = 1000
    
    print(f"[*] Sending {total_frames} frames...")
    start_time = time.time()
    
    for i in range(1, total_frames + 1):
        msg_id = i
        seq = i
        data = f"Frame {i}"
        
        send_frame(
            msg_type=MsgType.MSG,
            msg_id=msg_id,
            seq=seq,
            data=data,
            iface=iface,
            dst=dst,
            src=src,
            debug=False
        )
        
        if i % 100 == 0:
            print(f"[*] Sent {i}/{total_frames} frames")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"[*] Completed sending {total_frames} frames in {elapsed:.2f} seconds")
    print(f"[*] Average rate: {total_frames/elapsed:.2f} frames/sec")

if __name__ == "__main__":
    main()
