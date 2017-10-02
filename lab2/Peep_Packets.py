import zlib
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT8, UINT16, UINT32, UINT64,\
    STRING, BUFFER, BOOL, ComplexFieldType, PacketFields
from playground.network.packet.fieldtypes.attributes import Optional


class PEEP_Packet(PacketType):
    DEFINITION_IDENTIFIER = "PEEP-Packet"
    DEFINITION_VERSION = "1.0"

    """
    Types:
        0 - SYN
        1 - SYNACK
        2 - ACK
        3 - RIP
        4 - RIP-ACK
        5 - RST
        6 - Data
    """
    FIELDS = [
        ("Type", UINT8),
        ("SequenceNumber", UINT32({Optional: "True"})),
        ("Checksum", UINT16),
        ("Acknowledgement", UINT32({Optional: True})),
        ("Data", STRING({Optional: True}))
    ]

    def calculateChecksum(self):
        oldChecksum = self.Checksum
        self.Checksum = 0
        bytes = self.__serialize__()
        self.Checksum = oldChecksum
        return zlib.adler32(bytes) & 0xffff

    def updateChecksum(self):
        self.Checksum = self.calculateChecksum()

    def verifyChecksum(self):
        return self.Checksum == self.calculateChecksum()
