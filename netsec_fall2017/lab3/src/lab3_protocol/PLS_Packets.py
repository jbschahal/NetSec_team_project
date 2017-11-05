from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT8, UINT32, UINT64,\
    STRING, BUFFER, LIST, ComplexFieldType, PacketFields
from playground.network.packet.fieldtypes.attributes import Optional


class PlsBasePacket(PacketType):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.base"
    DEFINITION_VERSION = "1.0"
    FIELDS = []


class PlsHello(PlsBasePacket):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.hello"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("Nonce", UINT64),
        ("Certs", LIST(BUFFER))
    ]


class PlsKeyExchange(PlsBasePacket):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.keyexchange"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("PreKey", BUFFER),
        ("NoncePlusOne", UINT64)
    ]


class PlsHandshakeDone(PlsBasePacket):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.handshakedone"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("ValidationHash", BUFFER)
    ]


class PlsData(PlsBasePacket):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.data"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("Ciphertext", BUFFER),
        ("Mac", BUFFER)
    ]


class PlsClose(PlsBasePacket):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.close"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("Error", STRING({Optional: True}))
    ]
