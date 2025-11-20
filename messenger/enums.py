from enum import IntEnum

class MsgType(IntEnum):
    # Connection setup
    HANDSHAKE_REQ = 1  # port|name
    HANDSHAKE_ACK = 2  # port|name

    # Regular messaging
    MSG           = 3  # data
    MSG_ACK       = 4  # msg_id|seq
    MSG_RETRY     = 5  # msg_id|seq

    RENAME        = 6  # new_name
    RENAME_ACK    = 7  # none

    # File transfer
    FILE_INIT     = 8  # filename|size
    FILE_CHUNK    = 9  # data
    FILE_END      = 10 # none
    FILE_ACK      = 11 # msg_id|[seqs]

    # Control signals
    HEARTBEAT     = 12 # none
    TERMINATE     = 13 # none
