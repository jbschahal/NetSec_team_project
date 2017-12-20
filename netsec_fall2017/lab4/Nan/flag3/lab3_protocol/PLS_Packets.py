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

    def __repr__(self):
        certs = []
        for c in self.Certs:
            certs.append(str(c))
        return "PlsHello: \nNonce: " + str(self.Nonce) + "\nCerts: " + str(certs) + "\n"


class PlsKeyExchange(PlsBasePacket):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.keyexchange"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("PreKey", BUFFER),
        ("NoncePlusOne", UINT64)
    ]

    def __repr__(self):
        return "PlsKeyExchange: \nPreKey: " + str(self.PreKey) + "\nNoncePlusOne: " + str(self.NoncePlusOne) + "\n"


class PlsHandshakeDone(PlsBasePacket):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.handshakedone"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("ValidationHash", BUFFER)
    ]

    def __repr__(self):
        return "PlsHSDone: \nValidationHash: " + str(self.ValidationHash) + "\n"


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
