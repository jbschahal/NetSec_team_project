import asyncio
import OpenSSL
import playground
import hashlib
import cryptography
from OpenSSL import crypto
from . import CertFactory
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from playground.network.packet import PacketType
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
from playground.network.packet.fieldtypes import UINT8, UINT32, UINT64,\
    STRING, BUFFER, LIST, ComplexFieldType, PacketFields
from playground.network.packet.fieldtypes.attributes import Optional
from .PLS_Packets import PlsBasePacket, PlsHello, PlsKeyExchange,\
    PlsHandshakeDone, PlsData, PlsClose

sha256 = cryptography.hazmat.primitives.hashes.SHA256()
pkcs1v15 = padding.PKCS1v15()

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
        self.ekc = None
        self.eks = None
        self.ivc = None
        self.ivs = None
        self.mkc = None
        self.mks = None
        self.data_encryptor = None
        self.data_decryptor = None
        self.mac_creator = None
        self.mac_verifier = None

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
            block_0 = hashlib.sha1(b"PLS1.0" + self.client_nonce.to_bytes(8, 'big') + self.server_nonce.to_bytes(8, 'big') + self.pkc + self.pks).digest()
            block_1 = hashlib.sha1(block_0).digest()
            block_2 = hashlib.sha1(block_1).digest()
            block_3 = hashlib.sha1(block_2).digest()
            block_4 = hashlib.sha1(block_3).digest()

            block = block_0 + block_1 + block_2 + block_3 + block_4

            self.ekc = block[:128//8]
            self.eks = block[128//8:256//8]
            self.ivc = block[256//8:384//8]
            self.ivs = block[384//8:512//8]
            self.mkc = block[512//8:640//8]
            self.mks = block[640//8:768//8]


    def handle_data(self, packet):
        if (self.verify_mac(packet.Ciphertext, packet.Mac)):
            self.higherProtocol().data_received(self.decrypt_data(packet.Ciphertext))
        else:
            self.pls_close()

    def handle_close(self, packet):
        print("RECEIVED A CLOSE MESSAGE")
        self.transport.close()
        self.higherProtocol().connection_lost(None)

    def pls_close(self):
        close_packet = PlsClose()
        self.send_packet(close_packet)
        self.transport.close()
        self.higherProtocol().connection_lost(None)

    def transmit_data(self, data):
        self.encrypt_and_send(data)

    def connection_lost(self, exc):
        self.transport.close()
        self.transport = None

    def send_packet(self, packet):
        self.transport.write(packet.__serialize__())

    def encrypt_data(self, data):
        print("encrypt")
        return self.data_encryptor.update(data)

    def decrypt_data(self, data):
        return self.data_decryptor.update(data)

    def create_mac(self, data):
        temp = self.mac_creator.copy()
        temp.update(data)
        return temp.finalize()

    def verify_mac(self, data, mac):
        temp = self.mac_verifier.copy()
        temp.update(data)
        try:
            temp.verify(mac)
        except cryptography.exceptions.InvalidSignature as e:
            print(e)
            return False
        return True

    def encrypt_and_send(self, data):
        data_packet = PlsData()
        data_packet.Ciphertext = self.encrypt_data(data)
        data_packet.Mac = self.create_mac(data_packet.Ciphertext)
        self.send_packet(data_packet)

    def verify_certificate_chain(self, certs):
        if CertFactory.getRootCert("20174.1").encode() != certs[len(certs)-1]:
            self.pls_close()
            print("------------------------Root Cert Doesn't Match------------------------")
            return False
        past_cert = None
        past_pub_key = None
        try:
            for i in range(len(certs)):
                if past_cert == None and past_pub_key == None:
                    past_cert = crypto.load_certificate(crypto.FILETYPE_PEM, certs[i])
                    past_subject = self.get_cert_subject(past_cert)
                    past_issuer = self.get_cert_issuer(past_cert)
                    past_cert = past_cert.to_cryptography()
                    past_pub_key = past_cert.public_key()
                    continue
                if not self.ip_subset(past_subject, past_issuer):
                    return False
                current_cert = crypto.load_certificate(crypto.FILETYPE_PEM, certs[i])
                current_subject = self.get_cert_subject(current_cert)
                current_issuer = self.get_cert_issuer(current_cert)
                if past_issuer != current_subject:
                    return False
                current_cert = current_cert.to_cryptography()
                current_pub_key = current_cert.public_key()
                past_cert_tbs = past_cert.tbs_certificate_bytes
                current_pub_key.verify(past_cert.signature, past_cert_tbs, pkcs1v15, sha256)
                past_cert = current_cert
                past_pub_key = current_pub_key
                past_issuer = current_issuer
                past_subject = current_subject
        except cryptography.exceptions.InvalidSignature as e:
            print("----------------------Invalid Signature----------------------")
            return False
        return True

    def get_cert_subject(self, cert):
        for (a,b) in cert.get_subject().get_components():
            if a == b"CN":
                return b.decode()
        return None

    def get_cert_issuer(self, cert):
        for (a,b) in cert.get_issuer().get_components():
            if a == b"CN":
                return b.decode()
        return None

    def ip_subset(self, subject, issuer):
        subject = subject.split('.')
        issuer = issuer.split('.')
        if len(subject) - 1 != len(issuer):
            print("----------------------Fail IP subset 1----------------------")
            print("Size doesn't match")
            return False
        for i in range(min(len(subject), len(issuer))):
            if subject[i] != issuer[i]:
                print("----------------------Fail IP subset 2----------------------")
                print("Bad subset")
                return False
        return True



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
        self.protocol.pls_close()

    def abort(self):
        self.close()
