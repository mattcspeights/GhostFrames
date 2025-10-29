from enum import IntEnum

class MsgType(IntEnum):
    # Connection setup
    HANDSHAKE_REQ = 1  # port|name
    HANDSHAKE_ACK = 2  # port|name

    # Regular messaging
    MSG           = 3  # data
    MSG_ACK       = 4  # msg_id|seq
    MSG_RETRY     = 5  # msg_id|seq

    # File transfer
    FILE_INIT     = 6  # filename|size
    FILE_CHUNK    = 7  # data
    FILE_END      = 8  # none
    FILE_ACK      = 9  # msg_id|[seqs]

    # Control signals
    HEARTBEAT     = 10 # none (TODO)
    TERMINATE     = 11 # none
