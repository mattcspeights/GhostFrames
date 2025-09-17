from scapy.all import RadioTap, Dot11, sendp

pkt = RadioTap()/Dot11(type=2, subtype=0, addr1="ff:ff:ff:ff:ff:ff", 
                       addr2="aa:bb:cc:dd:ee:ff", addr3="aa:bb:cc:dd:ee:ff") \
     / b"GF|MSG|ID=01|SEQ=02|DATA=HELLO"

sendp(pkt, iface="wlan1mon", count=1, inter=0.1)