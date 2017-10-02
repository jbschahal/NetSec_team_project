import asyncio
import random
from Peep_Packets import PEEP_Packet
from playground.network.packet import PacketType
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory


class PEEP_Client(asyncio.Protocol):

    def __init__(self):
        self.transport = None
        self.deserializer = None

    def data_received(self, data):
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            if isinstance(packet, PEEP_Packet):
                print("Type of packet:")
                print(packet.Type)

    def connection_made(self, transport):
        print("client connection made")
        self.deserializer = PacketType.Deserializer()
        self.transport = transport
        #self.start_handshake()

    def connection_lost(self):
        self.transport = None

class PEEP_Passthrough2(StackingProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print("\nConnection made to the client middle layer\n")
        print(self.higherProtocol())
        self.higherProtocol().connection_made(StackingTransport(transport))

    def data_received(self, data):
        self.higherProtocol().data_received(data)

class PEEP_Passthrough1(StackingProtocol):
    def __init__(self):
        self.transport = None
        self.state = 0
        self.deserializer = None

    def data_received(self, data):
        if self.state == 1:
            # expecting a synack
            self.deserializer.update(data)
            for packet in self.deserializer.nextPackets():
                if isinstance(packet, PEEP_Packet):
                    if (packet.Type == 1):
                        # received a synack
                        if (packet.verifyChecksum()):
                            if packet.Acknowledgement == self.sequence_number + 1:
                                print("Received synack")
                                self.higherProtocol().connection_made(StackingTransport(self.transport))
                                print("connection_made to higher protocol: Middle layer")
                                print("Sending Back Ack")
                                self.transport.write(PEEP_Packet(Type=2, SequenceNumber=packet.Acknowledgement, \
                                    Acknowledgement=packet.SequenceNumber+1, Checksum = 0).__serialize__())
                                self.state = 2 # transmission state
        elif self.state == 2:
            #expecting a message packet
            print("Message data received")
            self.higherProtocol().data_received(data)

    def connection_made(self, transport):
        self.transport = transport
        elf.deserializer = PacketType.Deserializer()
        print("\nConnection made to lower client passthrough 1\n")
        #print(self.higherProtocol())
        #self.higherProtocol().connection_made(StackingTransport(transport))
    
    def start_handshake(self):
        self.sequence_number = random.randint(0,1000)
        print("Client start handshake")
        self.transport.write(PEEP_Packet(Type=0, SequenceNumber=self.sequence_number, Checksum=0).__serialize__())
        self.state = 1
