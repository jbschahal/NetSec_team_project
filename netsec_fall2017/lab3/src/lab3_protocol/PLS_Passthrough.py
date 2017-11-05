import random
import hashlib
import CertFactory
import cryptography
import OpenSSL
import serialization
from cryptography.hazmat.backends import default_backend
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT8, UINT32, UINT64,\
    STRING, BUFFER, LIST, ComplexFieldType, PacketFields
from playground.network.packet.fieldtypes.attributes import Optional
from .PLS_Base import PLS_Base, PLS_Transport
from .PLS_Packets import PlsBasePacket, PlsHello, PlsKeyExchange,\
    PlsHandshakeDone, PlsData, PlsClose

my_key_path = "~/netsec/keys/my.key"
cli_key_path = "~/netsec/keys/client.key"
server_key_path = "~/netsec/keys/server.key"
cert_dir = "~/netsec/certs/"
root_cert_path = cert_dir + "root.crt"
my_cert_path = cert_dir + "my.crt"
cli_cert_path = cert_dir + "client.crt"
server_cert_path = cert_dir + "server.crt"

sha256 = cryptography.hazmat.primitives.hashes.HashAlgorithm("sha256", digest_size=2048, block_size=2048)
mgf1 = cryptography.hazmat.primitives.asymmetric.padding.MGF1(sha256)
oaep = cryptography.hazmat.primitives.asymmetric.padding.OAEP(mgf1, sha256, None)


class PLS_Client(PLS_Base):

    def __init__(self):
        super().__init__()
        with open(cli_key_path, "rb") as key_file:
            self.my_priv_key = serialization.load_pem_private_key(\
                key_file.read(),\
                password = None,\
                backend = default_backend()\
            )

    def connection_made(self, transport):
        super().connection_made()
        self.start_handshake()

    def start_handshake(self):
        cli_hello = PlsHello()
        self.client_nonce = random.getrandbits(64)
        cli_hello.Nonce = self.clent_nonce
        my_cert = CertFactory.getCertsForAddr(my_cert_path)
        root_cert = CertFactory.getCertsForAddr(root_cert_path)
        cli_hello.Certs = [my_cert, root_cert]
        cli_hello.updateChecksum()
        self.m1 = cli_hello.__serialize__()
        self.send_packet(cli_hello)
        self.state = PLS_Base.HELLO

    def handle_hello(self, packet):
        self.m2 = packet.__serialize__()
        self.received_pub_key = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, packet.Certs[0]).get_pub_key().to_cryptography_key()
        self.state == PLS_Base.KEYEXCH
        keyexch_packet = PlsKeyExchange()
        self.pkc = "client pre key"
        keyexch_packet.PreKey = self.received_pub_key.encrypt(self.pkc, oaep)
        self.server_nonce = packet.Nonce
        keyexch_packet.NoncePlusOne = self.server_nonce + 1
        keyexch_packet.updateChecksum()
        self.m3 = keyexch_packet.__serialize__()
        self.send_packet(keyexch_packet)

    def handle_keyexch(self, packet):
        self.m4 = packet.__serialize__()
        self.pls = self.my_priv_key.decrypt(packet.PreKey, oaep)
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
        with open(server_key_path, "rb") as key_file:
            self.my_priv_key = serialization.load_pem_private_key(\
                key_file.read(),\
                password = None,\
                backend = default_backend()\
            )

    def connection_made(self, transport):
        super().connection_made()
        self.higherProtocol().transport = PLS_Transport(transport, self)

    def handle_hello(self, packet):
        self.m1 = packet.__serialize__()
        self.received_pub_key = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_EPM, packet.Certs[0]).get_pub_key().to_cryptography_key()
        self.state = PLS_Base.HELLO
        hello_packet = PlsHello()
        self.server_nonce = random.getrandbits(64)
        hello_packet.Nonce = self.server_nonce
        hello_packet.Certs = [my_cert_path, root_cert_path]
        hello_packet.updateChecksum()
        self.m2 = hello_packet.__serialize__()
        self.send_packet(hello_packet)
        self.state == PLS_Base.KEYEXCH
        keyexch_packet = PlsKeyExchange()
        self.pks = "server pre key"
        keyexch_packet.PreKey = self.received_pub_key.encrypt(self.pks, oaep)
        self.client_nonce = packet.Nonce
        keyexch_packet.NoncePlusOne = self.client_nonce + 1
        keyexch_packet.updateChecksum()
        self.m4 = keyexch_packet.__serialize__()
        self.send_packet(keyexch_packet)

    def handle_keyexch(self, packet):
        self.m3 = packet.__serialize__()
        self.pkc = self.my_priv_key.decrypt(packet.PreKey, oaep)
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
