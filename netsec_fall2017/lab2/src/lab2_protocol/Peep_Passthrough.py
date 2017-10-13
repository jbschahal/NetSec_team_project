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
        self.sequence_number = None
        self.acknowledgement = None
        self.base_sequence_number = None
        self.window_size = 5
        self.window_start = None
        self.window_end = None
        # when doing sliding windows, we can have a field:
        # self.bytes_acked = None
        self.data_size = None

    def data_received(self, data):
        print("peep_client: data received")
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            if isinstance(packet, PEEPPacket) and packet.verifyChecksum():
                self.handle_packets(packet)

    def handle_packets(self, packet):
        typenum = packet.Type
        if typenum == PEEPPacket.SYNACK and self.state == PEEP_Client.HANDSHAKE:
            print('peep_client: received SYNACK')
            self.handle_synack(packet)
        elif typenum == PEEPPacket.ACK and self.state == PEEP_Client.TRANS:
            print("peep_client: received ACK")
            self.handle_ack(packet)
        elif typenum == PEEPPacket.DATA and self.state == PEEP_Client.TRANS:
            print('peep_client: received Data')
            self.handle_data(packet)
        elif typenum == PEEPPacket.RIP and self.state == PEEP_Client.TRANS:
            print('peep_client: received RIP')
            self.handle_rip(packet)
        elif typenum == PEEPPacket.RIPACK and self.state == PEEP_Client.TEARDOWN:
            print('peep_client: received RIPACK')
            self.handle_ripack(packet)
        else:
            print('peep_client: received UNKNOWN TYPE')

    def handle_synack(self, packet):
        print("peep_client: Received synack")
        packet_to_send = PEEPPacket()
        packet_to_send.Type = PEEPPacket.ACK
        packet_to_send.SequenceNumber = packet.Acknowledgement
        self.base_sequence_number = packet.Acknowledgement
        self.sequence_number = self.base_sequence_number
        packet_to_send.Acknowledgement= packet.SequenceNumber+1
        packet_to_send.updateChecksum()
        print("peep_client: Sending Back Ack")
        self.transport.write(packet_to_send.__serialize__())
        self.state = PEEP_Client.TRANS # transmission state
        # Open upper layer transport
        print("peep_client: connection_made to higher protocol")
        self.higherProtocol().connection_made(PEEP_transport(self.transport, self))

    def handle_data(self, packet):
        print("peep_client: Message data received")
        self.acknowledgement = packet.SequenceNumber + len(packet.Data)
        ack_packet = PEEPPacket()
        ack_packet.Acknowledgement = self.acknowledgement
        ack_packet.Type = PEEPPacket.ACK
        ack_packet.updateChecksum()
        print('sending ack')
        self.transport.write(ack_packet.__serialize__())
        # TODO: make sure in order
        self.higherProtocol().data_received(packet.Data)

    def handle_ack(self, packet):
        print("peep_client: received ack")
        print("ack: ", packet.Acknowledgement)
#        self.sequence_number = packet.Acknowledgement
        self.window_start = max(self.window_start, packet.Acknowledgement)
        self.window_end = self.window_start + self.window_size * self.chunk_size
        self.send_window_data()
#        self.send_next_data()

    def handle_rip(self, packet):
        print('peep_client: checksum of RIP is correct')
        # Sending remaining packets back
        packetback = PEEPPacket()
        packetback.Acknowledgement = packet.SequenceNumber + 1
        packetback.Type = PEEPPacket.RIPACK
        packetback.updateChecksum()
        self.transport.write(packetback.__serialize__())
        print('peep_client: sent RIPACK')
        self.transport.close()

    def handle_ripack(self, packet):
        self.transport.close()


    def transmit_data(self, data, chunk_size):
        # TODO: need to append the data, not remove it.
        # Case: if protocol sends 2 consecutive packets, the 2nd packet
        # will replace the first packet.
        self.data = data
        self.data_size = len(data)
        self.chunk_size = chunk_size
        self.base_sequence_number = self.sequence_number
        self.window_start = self.base_sequence_number
        self.window_end = self.window_start
        print("transmitting data size: ", self.data_size)
        self.send_window_data()
#        self.send_next_data()

    def send_window_data(self):
        print('send window data')
        while self.window_end - self.window_start <= self.window_size * self.chunk_size:
            print("inside loop")
            print("wend: ", self.window_end)
            print("wstart: ", self.window_start)
            print("seq#: ", self.sequence_number)
            print("base seq#: ", self.base_sequence_number)

            if self.sequence_number - self.base_sequence_number >= self.data_size:
                print("all bytes have been sent from me")
                return
            self.send_next_chunk()
        print("end send window data")

    def send_next_chunk(self):
        print('send next chunk')
        packet = PEEPPacket()
        i = self.sequence_number - self.base_sequence_number
        packet.Type = PEEPPacket.DATA
        packet.SequenceNumber = self.sequence_number
        packet.Data = self.data[i:i+self.chunk_size]
        packet.updateChecksum()
        print("sending: " , packet.Data)
        print("sending: " , packet.SequenceNumber)
        self.transport.write(packet.__serialize__())
        self.sequence_number += len(packet.Data)
        self.window_end += len(packet.Data)

    def send_next_data(self):
        print("client send next data")
        if (self.sequence_number - self.base_sequence_number >= self.data_size):
            print("all bytes have been sent from me")
            return
        i = self.sequence_number - self.base_sequence_number
        data_packet = PEEPPacket(Type=PEEPPacket.DATA, Data=self.data[i:i+self.chunk_size])
        data_packet.SequenceNumber = self.sequence_number
        data_packet.updateChecksum()
        self.transport.write(data_packet.__serialize__())
        self.sequence_number += len(data_packet.Data)
#        self.bytes_sent += len(data_packet.Data)
        print("Data sent as:\nseq: " + str(data_packet.SequenceNumber) + "\nack: " + str(data_packet.Acknowledgement) + "\n datalen: " + str(len(data_packet.Data)))

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
        packet.Type = PEEPPacket.SYN
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
        self.base_sequence_number = None
        self.sequence_number = None
        self.acknowledgement = None
        self.data = None
        self.chunk_size = None
        self.window = 5
        self.data_size = None

    def connection_made(self,transport):
        print("peep_server: connection made")
        self.transport = transport
        self.higherProtocol().transport = PEEP_transport(transport, self)
        self.deserializer = PacketType.Deserializer()
        peername = transport.get_extra_info('peername')
        print('server(prepare)-->client(prepare):Connection from {}'.format(peername))

    def transmit_data(self, data, chunk_size):
        print("server transmit data")
        self.data = data
        self.data_size = len(data)
        self.chunk_size = chunk_size
        self.bytes_sent = 0
        self.base_sequence_number = self.sequence_number
        self.send_next_data()

    def send_next_data(self):
        print("server send next data")
        print("seq#: ", self.sequence_number)
        print("base_seq#: ", self.base_sequence_number)
        if (self.sequence_number - self.base_sequence_number >= self.data_size):
            print("all bytes have been sent from me")
            return
        i = self.sequence_number - self.base_sequence_number
        data_packet = PEEPPacket(Type=PEEPPacket.DATA, Data=self.data[i:i+self.chunk_size])
        data_packet.SequenceNumber = self.sequence_number
        data_packet.updateChecksum()
        self.transport.write(data_packet.__serialize__())
        self.sequence_number += len(data_packet.Data)
        print("Data sent as:\nseq: " + str(data_packet.SequenceNumber) + "\nack: " + str(data_packet.Acknowledgement) + "\n datalen: " + str(len(data_packet.Data)))
        print("data: ", data_packet.Data)

    def data_received(self,data):
        print("peep_server: data received")
        print("peep_server: data received2")
        self.deserializer.update(data)
        print("des update")
        for packet in self.deserializer.nextPackets():
            print("got a packet out")
            if isinstance(packet, PEEPPacket) and packet.verifyChecksum():
                self.handle_packets(packet)

    def handle_packets(self,packet):
        if isinstance(packet, PEEPPacket):
            typenum = packet.Type
            if typenum == PEEPPacket.SYN and self.state == PEEP_Server.INIT:
                print('peep_server: received SYN')
                self.handle_syn(packet)
            elif typenum == PEEPPacket.ACK:
                print('peep_server: received ACK')
                self.handle_ack(packet)
            elif typenum == PEEPPacket.RIP and self.state == PEEP_Server.TRANS:
                print('peep_server: received RIP')
                self.handle_rip(packet)
            elif typenum == PEEPPacket.RIPACK and self.state == PEEP_Server.TEARDOWN:
                print('peep_server: received RIPACK')
                self.handle_ripack(packet)
            elif typenum == PEEPPacket.DATA and self.state == PEEP_Server.TRANS:
                print('peep_server: received Data')
                self.handle_data(packet)
            else:
                print('peep_server: received UNKNOWN TYPE')
        else:
            print('peep_server:This packet is not a PEEPPacket')

    def handle_syn(self,packet):
        print('peep_server: checksum of SYN is correct')
        packetback = PEEPPacket()
        packetback.Acknowledgement = packet.SequenceNumber + 1
        packetback.SequenceNumber = random.randint(0,2**16)
        packetback.Type = PEEPPacket.SYNACK
        packetback.updateChecksum()
        self.transport.write(packetback.__serialize__())
        self.state = PEEP_Server.HANDSHAKE
        print('peep_server: sent SYNACK')

    def handle_ack(self,packet):
        if self.state == PEEP_Server.HANDSHAKE:
                print('peep_server: checksum of ACK is correct')
                print("ack: ", packet.Acknowledgement)
                # send data
                self.state = PEEP_Server.TRANS
                self.sequence_number = packet.Acknowledgement
                self.base_sequence_number = self.sequence_number
                # open upper layer transport
                self.higherProtocol().connection_made(PEEP_transport(self.transport, self))
        elif self.state == PEEP_Server.TRANS:
            #TODO: move window; send next packet
            self.sequence_number = packet.Acknowledgement
            self.send_next_data()

        else:
            print('peep_server: got ack in a bad state')
            self.transport.close()

    def handle_data(self, packet):
        print("peep_server: Message data received")
        print(packet)
        self.acknowledgement = packet.SequenceNumber + len(packet.Data)
        ack_packet = PEEPPacket()
        ack_packet.Acknowledgement = self.acknowledgement
        ack_packet.Type = PEEPPacket.ACK
        ack_packet.updateChecksum()
        self.higherProtocol().data_received(packet.Data)
        print("sending server ack")
        print("ack: ", self.acknowledgement)
        self.transport.write(ack_packet.__serialize__())
        # TODO: make sure in order

    def handle_rip(self,packet):
        print('peep_server: checksum of RIP is correct')
        # Sending remaining packets back
        packetback = PEEPPacket()
        packetback.Acknowledgement = packet.SequenceNumber + 1
        packetback.Type = PEEPPacket.RIPACK
        packetback.updateChecksum()
        self.transport.write(packetback.__serialize__())
        print('peep_server: sent RIPACK')
        self.transport.close()

    def handle_ripack(self,packet):
        self.transport.close()


class PEEP_transport(StackingTransport):

    def __init__(self, transport, protocol):
        self._lowerTransport = transport
        self.protocol = protocol
        self.transport = self._lowerTransport
        self.chunk_size = 1024

    def write(self, data):
        print("peep transport write")
        self.protocol.data = None
        self.protocol.transmit_data(data, self.chunk_size)

clientFactory = StackingProtocolFactory(PEEP_Client)
serverFactory = StackingProtocolFactory(PEEP_Server)
