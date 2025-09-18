from scapy.all import RadioTap, Dot11, sendp

def inject_frames(payload: bytes, iface: str, dst: str, src: str):
    dot11 = Dot11(
        type=2, subtype=0, # data frame
        addr1=dst,
        addr2=src,
        addr3="02:07:08:15:19:20"
    )
    pkt = RadioTap()/dot11/payload
    sendp(pkt, iface=iface, verbose=False)
    print(f"[+] Sent frame: {payload}")
