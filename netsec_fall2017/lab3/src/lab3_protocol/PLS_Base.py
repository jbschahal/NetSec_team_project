import asyncio
import OpenSSL
import playground
# import .CertFactory
import hashlib
from playground.network.packet import PacketType
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
from playground.network.packet.fieldtypes import UINT8, UINT32, UINT64,\
    STRING, BUFFER, LIST, ComplexFieldType, PacketFields
from playground.network.packet.fieldtypes.attributes import Optional
from .PLS_Packets import PlsBasePacket, PlsHello, PlsKeyExchange,\
    PlsHandshakeDone, PlsData, PlsClose


class PLS_Base(StackingProtocol):

    """
    State Machine:
        0: Init. Nothing has been sent. Client will be sending M1
        1: Hello. Client sent M1. Server received M1 and sends M2.
        2: KeyExch. Client received M2 and will send M3. Server received M3, send M4
        3: HSDone. Client will send M5. Server got M5 and will send M6.
        4: Secure. Client and server sends only encrypted data now.

    """

    INIT, HELLO, KEYEXCH, HSDONE, SECURE = [0,1,2,3,4]
#    received_nonces = []


    def __init__(self):
        self.transport = None
        self.deserializer = None
        self.state = PLS_Base.INIT
        self.client_nonce = None
        self.validation_hash = None
        self.data = None
        self.pkc = None
        self.pks = None
        self.server_nonce = None
        self.m1 = None
        self.m2 = None
        self.m3 = None
        self.m4 = None
        self.my_pub_key = None
        self.received_pub_key = None
        self.my_priv_key = None
        self.shared_key = None

        self.ekc = None
        self.eks = None
        self.ivc = None
        self.ivs = None
        self.mkc = None
        self.mks = None

    def connection_made(self, transport):
        self.transport = transport
        self.deserializer = PlsBasePacket.Deserializer()

    def data_received(self, data):
        print("pls data received")
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            if isinstance(packet, PlsBasePacket):
                self.handle_packets(packet)

    def handle_packets(self, packet):
        if isinstance(packet, PlsHello):
            print("got pls hello")
            self.handle_hello(packet)
        elif isinstance(packet, PlsKeyExchange):
            self.handle_keyexch(packet)
        elif isinstance(packet, PlsHandshakeDone):
            self.handle_hsdone(packet)
        elif isinstance(packet, PlsData):
            self.handle_data(packet)
        elif isinstance(packet, PlsClose):
            self.handle_close(packet)
        else:
            print("got packet in a bad state.", "Packet:", packet, "State:", self.state)

    def handle_hsdone(self, packet):
        if self.validation_hash != packet.ValidationHash:
            print("error: validation hash doesn't match")
            self.pls_close()
        else:
            block_0 = hashlib.sha1(b"PLS1.0" + str(self.client_nonce).encode() + str(self.server_nonce).encode() + self.pkc + self.pks).digest()
            block_1 = hashlib.sha1(block_0).digest()
            block_2 = hashlib.sha1(block_1).digest()
            block_3 = hashlib.sha1(block_2).digest()
            block_4 = hashlib.sha1(block_3).digest()

            block = block_0 + block_1 + block_2 + block_3 + block_4

            self.ekc = block[:128]
            self.eks = block[128:256]
            self.ivc = block[256:384]
            self.ivs = block[384:512]
            self.mkc = block[512:640]
            self.mks = block[640:768]

            self.encrypt_and_send(self.data)

    def handle_close(self, packet):
        self.transport.close()
        self.higherProtocol().connection_lost(None)

    def pls_close(self):
        close_packet = PlsClose()
        self.send_packet(close_packet)

    def transmit_data(self, data):
        self.transport.write(data)

    def connection_lost(self, exc):
        self.transport.close()
        self.transport = None
        asyncio.get_event_loop().stop()

    def send_packet(self, packet):
        self.transport.write(packet.__serialize__())

    def encrypt_and_send(self, data):
        pass


class PLS_Transport(StackingTransport):
    def __init__(self, transport, protocol):
        super().__init__(transport)
        self._lowerTransport = transport
        self.protocol = protocol
        self.transport = self._lowerTransport

    def write(self, data):
        print("pls transport write")
        self.protocol.transmit_data(data)

    def close(self):
        self.protocol.initiate_teardown()

    def abort(self):
        self.protocol.abort_connection()
