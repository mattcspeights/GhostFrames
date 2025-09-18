from scapy.all import sniff, Dot11

def sniff_frames(iface: str, bssid: str, filter_substring: bytes = None):
    def handler(pkt):
        if pkt.haslayer(Dot11):
            dot11 = pkt[Dot11]
            # Only match frames with the right pseudo-BSSID
            if dot11.addr3 == bssid and pkt.haslayer(Raw):
                payload = pkt[Raw].load
                if filter_substring is None or filter_substring in payload:
                    print(f"[+] Received: {payload}")

    sniff(iface=iface, prn=handler, store=0)
