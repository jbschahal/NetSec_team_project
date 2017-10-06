import asyncio
import random
import playground
from .Peep_Packets import PEEPPacket
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
from playground.network.packet import PacketType

class PEEP_Client(StackingProtocol):

    """
    State Definitions:
        0 - INIT:  we haven't done anything.
        1 - HANDSHAKE: we sent an syn and waiting for server to respond
        2 - TRANS: data transmission. we can also send a rip from this state
        3 - TEARDOWN: we received a RIP from the server. send rip ack and close.
    """

    INIT, HANDSHAKE, TRANS, TEARDOWN = [0,1,2,3]

    def __init__(self):
        super().__init__()
        self.transport = None
        self.state = PEEP_Client.INIT
        self.deserializer = None

    def data_received(self, data):
        print("peep_client: data received")
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            if isinstance(packet, PEEPPacket):
                if self.state == PEEP_Client.HANDSHAKE:
                    # expecting a synack
                    if (packet.Type == PEEPPacket.SYNACK):
                        # received a synack
                        if packet.verifyChecksum() and packet.Acknowledgement == self.sequence_number + 1:
                            print("peep_client: Received synack")
                            packet_to_send = PEEPPacket()
                            packet_to_send.Type = PEEPPacket.ACK
                            packet_to_send.SequenceNumber = packet.Acknowledgement
                            packet_to_send.Acknowledgement= packet.SequenceNumber+1
                            packet_to_send.updateChecksum()
                            print("peep_client: Sending Back Ack")
                            self.transport.write(packet_to_send.__serialize__())
                            self.state = PEEP_Client.TRANS # transmission state
                            # Open upper layer transport
                            print("peep_client: connection_made to higher protocol")
                            print("peep_client: connection_made to higher protocol")
                            self.higherProtocol().connection_made(PEEP_transport(self.transport, self))
                        else:
                            self.transport.close()
                elif self.state == PEEP_Client.TRANS:
                    # expecting a message packet
                    # TODO: if checksum bad, then don't respond
                    # TODO: if checksum bad, then don't respond

                    if packet.Type == PEEPPacket.DATA:
                        print("peep_client: Message data received")
                        self.higherProtocol().data_received(packet.Data)

                    #test chunk slicing
                    data=b'aaaaaaaaaaaaaaaaaaaaa'
                    self.higherProtocol().PEEP_transport.write(self,data)

    def connection_made(self, transport):
        self.transport = transport
        self.deserializer = PacketType.Deserializer()
        self.start_handshake()

    def connection_lost(self, exc):
        self.transport.close()
        self.transport = None

    def start_handshake(self):
        self.sequence_number = random.randint(0,2**16)
        print("peep_client: start handshake")
        packet = PEEPPacket()
        packet.Type = self.state
        packet.SequenceNumber = self.sequence_number
        packet.updateChecksum()
        self.transport.write(packet.__serialize__())
        self.state = PEEP_Client.HANDSHAKE

class PEEP_Server(StackingProtocol):

    """
    State Definitions:
        0 - INIT: we have not received any connections
        1 - HANDSHAKE: we received a syn and sent a synack. waiting for ack
        2 - TRANS: getting data
        3 - TEARDOWN: received a rip, sent rip ack; sent a rip, waiting for ripack
    """

    INIT, HANDSHAKE, TRANS, TEARDOWN = [0,1,2,3]

    def __init__(self):
        super().__init__()
        self.transport = None
        self.deserializer = None
        self.state = PEEP_Server.INIT

    def connection_made(self,transport):
        print("peep_server: connection made")
        self.transport = transport
        self.higherProtocol().transport = PEEP_transport(transport, self)
        self.deserializer = PacketType.Deserializer()
        peername = transport.get_extra_info('peername')
        print('server(prepare)-->client(prepare):Connection from {}'.format(peername))

    def data_received(self,data):
        print("peep_server: data received")
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            self.handle_packets(pkt)

    def handle_packets(self,pkt):
        if isinstance(pkt, PEEPPacket):
            typenum = pkt.Type
            if typenum == PEEPPacket.SYN and self.state == PEEP_Server.INIT:
                print('peep_server: received SYN')
                self.handle_syn(pkt)
            elif typenum == PEEPPacket.ACK and self.state == PEEP_Server.HANDSHAKE:
                print('peep_server: received ACK')
                self.handle_ack(pkt)
            elif typenum == PEEPPacket.RIP and self.state == PEEP_Server.TRANS:
                print('peep_server: received RIP')
                self.handle_rip(pkt)
            elif typenum == PEEPPacket.RIPACK and self.state == PEEP_Server.TEARDOWN:
                print('peep_server: received RIPACK')
                self.handle_ripack(pkt)
            elif typenum == PEEPPacket.DATA and self.state == PEEP_Server.TRANS:
                print('peep_server: received Data')
                self.handle_data(pkt)
            else:
                print('peep_server: received UNKNOWN TYPE')
        else:
            print('peep_server:This packet is not a PEEPPacket')

    def handle_syn(self,pkt):
        if pkt.verifyChecksum():
            print('peep_server: checksum of SYN is correct')
            pktback = PEEPPacket()
            pktback.Acknowledgement = pkt.SequenceNumber + 1
            pktback.SequenceNumber = random.randint(0,2**16)
            pktback.Type = PEEPPacket.SYNACK
            pktback.updateChecksum()
            self.transport.write(pktback.__serialize__())
            self.state = PEEP_Server.HANDSHAKE
            print('peep_server: sent SYNACK')
        else:
            print('peep_server: checksum of SYN is incorrect')
            self.transport.close()

    def handle_ack(self,pkt):
        if pkt.verifyChecksum():
            print('peep_server: checksum of ACK is correct')
            # send data
            self.state = PEEP_Server.TRANS
            # open upper layer transport
            #data=b'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
            self.higherProtocol().connection_made(PEEP_transport(self.transport, self))

        else:
            print('peep_server: checksum of ACK is incorrect')
            self.transport.close()

    def handle_data(self, pkt):
        if pkt.verifyChecksum():
            print('peep_server: checksum of data is correct')
            self.higherProtocol().data_received(pkt.Data)
        else:
            print("pee_server: checksum of data is incorrect")

    def handle_rip(self,pkt):
        if pkt.verifyChecksum():
            print('peep_server: checksum of RIP is correct')
            # Sending remaining packets back
            pktback = PEEPPacket()
            pktback.Acknowledgement = pkt.SequenceNumber + 1
            pktback.Type = PEEPPacket.RIPACK
            pktback.updateChecksum()
            self.transport.write(pktback.__serialize__())
            print('peep_server: sent RIPACK')
            self.transport.close()

    def handle_ripack(self,pkt):
        if pkt.verifyChecksum():
            print('peep_server: checksum of RIPACK is correct')
        else:
            print('peep_server: checksum of RIPACK is incorrect')
        self.transport.close()

class PEEP_transport(StackingTransport):

    def __init__(self, transport, protocol):
            self._lowerTransport = transport
            self.protocol = protocol
            self.transport = self._lowerTransport

    def write(self, data):
            print("peep transport write")
            # TODO: need a proper sequence number
            # slice the data chunk
            chunk_size = 10

            chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

            data_packet = PEEPPacket(Type=PEEPPacket.DATA)

            if self.protocol.acknowledgmnet_received == None:
                if self.protocol.sequence_number_received == None:
                    # First data sent
                    data_packet.SequenceNumber = random.randint(0, 2 ** 16)


                # First data received
                else:
                    data_packet.Acknowledgement = self.protocol.generate_ack()

            for i in range(0, len(chunks) - 1):

                data_packet.SequenceNumber+=i
                data_packet.DATA=chunks[i]
                print("send the %d packets in windows", i)
                data_packet.updateChecksum()
                self.transport.write(data_packet.__serialize__())







#    def close(self):
#        self._lowerTransport.close()
#        self.transport = None


clientFactory = StackingProtocolFactory(PEEP_Client)
serverFactory = StackingProtocolFactory(PEEP_Server)