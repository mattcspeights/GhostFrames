from inject import inject
inject(b"GF|MSG|ID=01|SEQ=02|DATA=HELLO",
           iface="wlan1mon",
           dst="ff:ff:ff:ff:ff:ff",
           src="aa:bb:cc:dd:ee:ff")
