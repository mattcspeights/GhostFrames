from datetime import datetime
from scapy.all import RadioTap, Dot11, LLC, SNAP, Raw, sendp
from payload_utils import build_payload
from enums import MsgType
from crypto_utils import encrypt_data

def send_frame(msg_type: MsgType, msg_id: int, seq: int, data: str,
                  iface: str, dst: str, src: str, debug: bool = True):
    # Encrypt the data before building the payload
    encrypted_data = encrypt_data(data) if data else ""
    
    dot11 = Dot11(type=2, subtype=0, addr1=dst, addr2=src, addr3="02:07:08:15:19:20")
    payload = build_payload(msg_type, msg_id, seq, encrypted_data)
    pkt = RadioTap()/dot11/LLC()/SNAP()/Raw(payload)
    sendp(pkt, iface=iface, verbose=False)
    if debug:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] Sent frame (encrypted): {payload!r}")
