from datetime import datetime
from scapy.all import sniff, Dot11, Raw
from payload_utils import parse_payload
from enums import MsgType

def sniff_frames(iface: str, filter_substring: bytes = None, debug: bool = True, callback=None):
    def handler(pkt):
        if pkt.haslayer(Dot11):
            dot11 = pkt[Dot11]
            # Only match frames with the right pseudo-BSSID
            # TODO: also only match frames with the right source address post-handshake
            if dot11.addr3 == "02:07:08:15:19:20" and pkt.haslayer(Raw):
                payload = pkt[Raw].load
                if filter_substring is None or filter_substring in payload:
                    parsed = parse_payload(payload)
                    if parsed:
                        msg_type, msg_id, seq, data = parsed
                        
                        # Call the callback function if provided
                        if callback:
                            callback(pkt, msg_type, msg_id, seq, data)
                        elif debug:
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"[{timestamp}] Received frame:")
                            print(f"    Type: {msg_type.name} ({msg_type.value})")
                            print(f"    ID:   {msg_id}")
                            print(f"    Seq:  {seq}")
                            print(f"    Data: {data}")
                    else:
                        if debug:
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"[{timestamp}] Received unparseable payload: {payload!r}")

    sniff(iface=iface, prn=handler, store=0)
