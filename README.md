# Ghost Frames

## Overview

**Ghost Frames** is a custom communication system that leverages low-level 802.11 wireless frames to transmit messages outside the standard TCP/IP stack. The project aims to create a secure way to deliver messages and files between users, ultimately through a user-facing desktop application.  

## Instructions

To use this project, run messenger/peer.py.  


## Frame Parameters

All of our frames will be `Dot11(type=2, subtype=0) (data)` frames.

```py
addr1="ff:ff:ff:ff:ff:ff"   # dst MAC address. for discovery, this will be all `f`. 
addr2="aa:bb:cc:dd:ee:ff",  # src, this will always be set since we know what our own MAC is.  
addr3="01:07:08:15:19:20"   # For IBSS, we can choose an arbitrary BSSID (this spells ghost).   
```

To use, call: `inject_frames(msg_type, msg_id, seq, data, iface, dst, src)`

`iface` will be: `wlan1mon`

Example payload:

`"GF|3|0001|0004|hello world!"`

- `header = b"GF"`: Ghost Frames Identifier (keep this the same)
- `msg_type = MsgType.MSG (3)`
- `msg_id = 0001`: message id (can have multiple frames for a single message)
- `seq = 0004`: sequence number
- `msg = "hello world!"`: message info


## Authors

- Matthew Speights - mattcspeights@tamu.edu
- Jason Somervell - jasonsomervell@tamu.edu
- Tam Pham - tam001p@tamu.edu
- Shawn Gao - shawng3884@tamu.edu