import socket

s = socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.ntohs(3))
s.bind(("wlanusb3", 0))
while True:
    packet = s.recv(65535)
    radiotap_hdr_len = packet[2] | (packet[3] << 8)
    payload = packet[radiotap_hdr_len+24:-4]
    if b"hello" in payload:
        print(payload)
