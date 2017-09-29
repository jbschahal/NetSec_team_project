from playground.network.packet import PacketType, FIELD_NOT_SET
from playground.network.packet.fieldtypes import UINT8, UINT16, UINT32, UINT64,\
    STRING, BUFFER, BOOL, ComplexFieldType, PacketFields
from playground.network.packet.fieldtypes.attributes import Optional


class PEEP_Packet(PacketType):
    DEFINITION_IDENTIFIER = "PEEP-Packet"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Type", UINT8),
        ("SequenceNumber", UINT32({Optional: "True"})),
        ("Checksum", UINT16),
        ("Acknowledgement", UINT32({Optional: True})),
        ("Data", STRING({Optional: True}))
    ]
