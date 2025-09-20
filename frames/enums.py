from enum import IntEnum

class MsgType(IntEnum):
    HANDSHAKE_REQ = 1
    HANDSHAKE_ACK = 2
    MSG           = 3
    MSG_ACK       = 4
    MSG_RETRY     = 5
    HEARTBEAT     = 6
    TERMINATE     = 7