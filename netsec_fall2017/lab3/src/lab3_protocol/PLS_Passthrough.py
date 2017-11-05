import random
import hashlib
import CertFactory
import OpenSSL
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT8, UINT32, UINT64,\
    STRING, BUFFER, LIST, ComplexFieldType, PacketFields
from playground.network.packet.fieldtypes.attributes import Optional
from .PLS_Base import PLS_Base, PLS_Transport
from .PLS_Packets import PlsBasePacket, PlsHello, PlsKeyExchange,\
    PlsHandshakeDone, PlsData, PlsClose

key_path = "~/netsec/keys/netsecfa17.key"
cert_dir = "~/netsec/certs/"
root_cert_path = cert_dir + "root.crt"
my_cert_path = cert_dir + "my.crt"
cli_cert_path = cert_dir + "client.crt"
server_cert_path = cert_dir + "server.crt"

sha256 = cryptography.hazmat.primitives.hashes.HashAlgorithm("sha256", digest_size=2048, block_size=2048)
mgf1 = cryptography.hazmat.primitives.asymmetric.padding.MGF1(sha256)
oaep = cryptography.hazmat.primitives.asymmetric.padding.OAEP


class PLS_Client(PLS_Base):

    def __init__(self):
        super().__init__()

    def connection_made(self, transport):
        super().connection_made()
        self.start_handshake()

    def start_handshake(self):
        cli_hello = PlsHello()
        self.nonce = random.getrandbits(64)
        cli_hello.Nonce = self.nonce
        my_cert = CertFactory.getCertsForAddr(my_cert_path)
        root_cert = CertFactory.getCertsForAddr(root_cert_path)
        cli_hello.Certs = [my_cert, root_cert]
        cli_hello.updateChecksum()
        self.m1 = cli_hello
        self.send_packet(cli_hello)
        self.state = PLS_Base.HELLO

    def handle_hello(self, packet):
        self.m2 = packet
        self.received_pub_key = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, packet.Certs[0]).get_pub_key().to_cryptography_key()
        self.state == PLS_Base.KEYEXCH
        keyexch_packet = PlsKeyExchange()
        self.pkc = "client pre key"
        keyexch_packet.PreKey = self.received_pub_key.encrypt(self.pkc, \
                                                              cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                                                                cryptography.hazmat.primitives.asymmetric.padding.MGF1(),

                                                              ))
        keyexch_packet.PreKey = self.client_pre_key #TODO: encrypt this under pub key from S
        self.received_nonce = packet.Nonce
        keyexch_packet.NoncePlusOne = self.received_nonce + 1
        keyexch_packet.updateChecksum()
        self.m3 = keyexch_packet
        self.send_packet(keyexch_packet)

    def handle_keyexch(self, packet):
        self.m4 = packet
        self.pks = packet.PreKey #TODO: decrypt this uinsg my priv key
        hsdone_packet = PlsHandshakeDone()
        messages_hash = hashlib.sha1()
        messages_hash.update(self.m1)
        messages_hash.update(self.m2)
        messages_hash.update(self.m3)
        messages_hash.update(self.m4)
        self.validation_hash = messages_hash.digest()
        hsdone_packet.ValidationHash = self.validation_hash
        hsdone_packet.updateChecksum()
        self.send_packet(hsdone_packet)


class PLS_Server(PLS_Base):

    def __init__(self):
        super().__init__()

    def connection_made(self, transport):
        super().connection_made()
        self.higherProtocol().transport = PLS_Transport(transport, self)

    def handle_hello(self, packet):
        self.m1 = packet
        # TODO: extract pub key from C cert
        self.state = PLS_Base.HELLO
        hello_packet = PlsHello()
        self.nonce = random.getrandbits(64)
        hello_packet.Nonce = self.nonce
        hello_packet.Certs = [my_cert_path, root_cert_path]
        hello_packet.updateChecksum()
        self.m2 = hello_packet
        self.send_packet(hello_packet)
        self.state == PLS_Base.KEYEXCH
        keyexch_packet = PlsKeyExchange()
        self.pks = "server pre key"
        keyexch_packet.PreKey = self.server_pre_key #TODO: encrypt this under pub key from C
        self.received_nonce = packet.Nonce
        keyexch_packet.NoncePlusOne = self.received_nonce + 1
        keyexch_packet.updateChecksum()
        self.m4 = keyexch_packet
        self.send_packet(keyexch_packet)

    def handle_keyexch(self, packet):
        self.m3 = packet
        self.pkc = packet.PreKey #TODO: decrypt this using my priv key
        hsdone_packet = PlsHandshakeDone()
        messages_hash = hashlib.sha1()
        messages_hash.update(self.m1)
        messages_hash.update(self.m2)
        messages_hash.update(self.m3)
        messages_hash.update(self.m4)
        self.validation_hash = messages_hash.digest()
        hsdone_packet.ValidationHash = self.validation_hash
        hsdone_packet.updateChecksum()
        self.send_packet(hsdone_packet)
