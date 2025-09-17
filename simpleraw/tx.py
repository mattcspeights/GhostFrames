import socket, struct, time

sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
sock.bind(("wlan1mon", 0))
def send(payload):
    src = bytes.fromhex("deadbeef0001")
    dst = bytes.fromhex("ffffffffffff")
    bss = bytes.fromhex("cafed00d9999")
    radio_tap_header = bytes.fromhex("0000080000000000")
    dot11_header = struct.pack('<BBH6s6s6sH', 0x08, 0x00, 0, dst, src, bss, 0)
    sock.send(radio_tap_header + dot11_header + payload)

for i in range(1000000):
    send(f"hello world {i}".encode())
    time.sleep(0.2)
