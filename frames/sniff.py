from scapy.all import sniff

def handle(pkt):
    if pkt.haslayer(Dot11):
        payload = bytes(pkt.payload)
        if b"GF" in payload:
            print("Ghost Frame:", payload)

sniff(iface="en0", prn=handle)