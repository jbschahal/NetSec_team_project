import asyncio
import random
from Peep_Packets import PEEP_Packet
from playground.network.packet import PacketType

class PEEP_Client(asyncio.Protocol):

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
                        if (packet.Checksum == 0):
                            if packet.Acknowledgement == self.sequence_number + 1:
                                print("Received synack; sending ack")
                                self.transport.write(PEEP_Packet(Type=2, SequenceNumber=packet.Acknowledgement, \
                                    Acknowledgement=packet.SequenceNumber+1, Checksum = 0).__serialize__())
                                self.state = 2 # transmission state

    def connection_made(self, transport):
        print("client connection made")
        self.deserializer = PacketType.Deserializer()
        self.transport = transport
        #self.start_handshake()

    def connection_lost(self):
        self.transport = None

    def start_handshake(self):
        self.sequence_number = random.randint(0,1000)
        print("Client start handshake")
        self.transport.write(PEEP_Packet(Type=0, SequenceNumber=self.sequence_number, Checksum=0).__serialize__())
        self.state = 1

