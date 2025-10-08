from enum import IntEnum

class MsgType(IntEnum):
    HANDSHAKE_REQ = 1 # port|name
    HANDSHAKE_ACK = 2 # port|name
    MSG           = 3 # data
    MSG_ACK       = 4 # msg_id|seq
    MSG_RETRY     = 5 # msg_id|seq
    HEARTBEAT     = 6 # none (TODO)
    TERMINATE     = 7 # none (TODO)