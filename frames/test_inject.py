from inject_frames import inject_frames
from enums import MsgType

def main():
    iface = "wlan1mon"
    dst = "ff:ff:ff:ff:ff:ff"
    src = "aa:bb:cc:dd:ee:ff"

    msg_id = 1
    seq = 1

    print("[*] Type q to exit.")
    while True:
        data = input("Enter message: ").strip()
        if data.lower() in ("q"):
            print("[*] Exiting injector.")
            break

        inject_frames(
            msg_type=MsgType.MSG,
            msg_id=msg_id,
            seq=seq,
            data=data,
            iface=iface,
            dst=dst,
            src=src
        )

        msg_id += 1
        seq += 1

if __name__ == "__main__":
    main()
