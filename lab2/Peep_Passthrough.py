import asyncio
import random
import playground
from Peep_Packets import PEEP_Packet
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
from playground.network.packet import PacketType

class PEEP_1a(StackingProtocol):
    def __init__(self):
        super().__init__()
        self.transport = None
        self.state = 0
        self.deserializer = None

    def data_received(self, data):
        self.deserializer.update(data)
        if self.state == 1:
            # expecting a synack
            for packet in self.deserializer.nextPackets():
                if isinstance(packet, PEEP_Packet):
                    if (packet.Type == 1):
                        # received a synack
                        if packet.verifyChecksum() and packet.Acknowledgement == self.sequence_number + 1:
                            print("peep1a: Received synack")
                            packet_to_send = PEEP_Packet()
                            packet_to_send.Type = 2
                            packet_to_send.SequenceNumber = packet.Acknowledgement
                            packet_to_send.Acknowledgement= packet.SequenceNumber+1
                            packet_to_send.updateChecksum()
                            print("peep1a: Sending Back Ack")
                            self.transport.write(packet_to_send.__serialize__())
                            self.state = 2 # transmission state
                            # Open upper layer transport
                            print("peep1a: connection_made to higher protocol")
                            self.higherProtocol().connection_made(self.transport)
                        else:
                            self.transport.close()
        elif self.state == 2:
            # expecting a message packet
            print("peep1a: Message data received")
            if self.higherProtocolConnectionMade == True:
                self.higherProtocol().data_received(data)

    def connection_made(self, transport):
        self.transport = StackingTransport(transport)
        self.deserializer = PacketType.Deserializer()
        self.start_handshake()

    def connection_lost(self, exc):
        self.transport.close()
        self.transport = None

    def start_handshake(self):
        self.sequence_number = random.randint(0,2**16)
        print("peep1a: start handshake")
        packet = PEEP_Packet()
        packet.Type = self.state
        packet.SequenceNumber = self.sequence_number
        packet.updateChecksum()
        self.transport.write(packet.__serialize__())
        self.state = 1

class PEEP_1b(StackingProtocol):
    def __init__(self):
        super().__init__()
        self.transport = None
        self.deserializer = None
        self.state = 0

    def connection_made(self,transport):
        print("peep1b: connection made")
        self.transport = StackingTransport(transport)
        self.deserializer = PacketType.Deserializer()
        peername = transport.get_extra_info('peername')
        print('server(prepare)-->client(prepare):Connection from {}'.format(peername))

    def data_received(self,data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            self.handle_packets(pkt)

    def handle_packets(self,pkt):
        if isinstance(pkt, PEEP_Packet):
            typenum = pkt.Type
            if typenum == 0 and self.state == 0:
                print('peep1b: received SYN')
                self.handle_syn(pkt)
            elif typenum == 2 and self.state == 1:
                print('peep1b: received ACK')
                self.handle_ack(pkt)
            elif typenum == 3 and self.state == 2:
                print('peep1b: received RIP')
                self.handle_rip(pkt)
            elif typenum == 4 and self.state == 2:
                print('peep1b: received RIPACK')
                self.handle_ripack(pkt)
            else:
                # handle data packets?
                print('peep1b: received UNKNOWN TYPE')
                #if self.higherProtocolConnectionMade == True:
                #    self.higherProtocol().data_received(data)
        else:
            print('peep1b:This packet is not a PEEP_Packet')

    def handle_syn(self,pkt):
        if pkt.verifyChecksum():
            print('peep1b: checksum of SYN is correct')
            pktback = PEEP_Packet()
            pktback.Acknowledgement = pkt.SequenceNumber + 1
            pktback.SequenceNumber = random.randint(0,100)
            pktback.Type = 1
            pktback.updateChecksum()
            self.transport.write(pktback.__serialize__())
            self.state += 1
            print('peep1b: sent SYNACK')
        else:
            print('peep1b: checksum of SYN is incorrect')
            pktback = PEEP_Packet()
            pktback.Type = 5
            pktback.updateChecksum()
            self.transport.write(pktback.__serialize__())
            print('peep1b: sent RST')
            # clear buffer
            self.transport.close()

    def handle_ack(self,pkt):
        if pkt.verifyChecksum():
            print('peep1b: checksum of ACK is correct')
            # send data
            self.state += 1
            # open upper layer transport
            self.higherProtocol().connection_made(self.transport)
        else:
            print('peep1b: checksum of ACK is incorrect')
            pktback = PEEP_Packet()
            pktback.Type = 5
            pktback.updateChecksum()
            self.transport.write(pktback.__serialize__())
            self.transport.close()
            print('peep1b: sent RST')

    def handle_rip(self,pkt):
        if pkt.verifyChecksum():
            print('peep1b: checksum of RIP is correct')
            pktback = PEEP_Packet()
            pktback.Acknowledgement = pkt.SequenceNumber + 1
            pktback.Type = 4
            pktback.updateChecksum()
            self.transport.write(pktback.__serialize__())
            print('peep1b: sent RIPACK')
            # Sending remaining packets back
            pktback2 = PEEP_Packet()
            pktback2.Acknowledgement = pkt.SequenceNumber + 1
            pktback2.Type = 3
            pktback2.updateChecksum()
            pktback2.SequenceNumber = random.randint(0,100)
            self.transport.write(pktback2.__serialize__())
            print('peep1b: sent RIP')
        else:
            print('peep1b: checksum of RIP is incorrect')
            pktback = PEEP_Packet()
            pktback.Type = 5
            pktback.updateChecksum()
            self.transport.write(pktback.__serialize__())
            #if self.higherProtocolConnectionMade == True:
            #    self.higherProtocol().transport.close()
            #    self.higherProtocolConnectionMade = False
            self.transport.close()
            print('peep1b: sent RST')

    def handle_ripack(self,pkt):
        if pkt.verifyChecksum():
            print('peep1b: checksum of RIPACK is correct')
            #if self.higherProtocolConnectionMade == True:
            #    self.higherProtocol().transport.close()
            #    self.higherProtocolConnectionMade = False
            self.transport.close()
        else:
            print('peep1b: checksum of RIPACK is incorrect')
            #if self.higherProtocolConnectionMade == True:
            #    self.higherProtocol().transport.close()
            #    self.higherProtocolConnectionMade = False
            self.transport.close()