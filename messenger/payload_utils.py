from enums import MsgType
from scapy.all import get_if_hwaddr

def build_payload(msg_type: MsgType, msg_id: int, seq: int, data: str = "") -> bytes:
    """
    Build a payload string.
    """
    payload = f"GF|{msg_type:02d}|{msg_id:04d}|{seq:04d}|{data}"
    return payload.encode()

def parse_payload(payload: bytes):
    """
    Parse a payload and return components.
    Returns (msg_type, msg_id, seq, data) or None if parsing fails.
    """
    try:
        parts = payload.decode().split("|")
        if parts[0] != "GF":
            return None
        msg_type = MsgType(int(parts[1]))
        msg_id   = int(parts[2])
        seq      = int(parts[3])
        data     = "|".join(parts[4:]) if len(parts) > 4 else ""
        return msg_type, msg_id, seq, data
    except Exception:
        return None

def get_mac(interface):
    """
    Get the MAC address of a network interface using scapy.
    """
    try:
        return get_if_hwaddr(interface)
    except:
        print(f"Error: Could not get MAC address for {interface}, using default MAC")
        return "aa:bb:cc:dd:ee:ff"