import asyncio
import random
import playground
from .Peep_Packets import PEEPPacket
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
from playground.network.packet import PacketType

class PEEP_Base(StackingProtocol):

    INIT, HANDSHAKE, TRANS, TEARDOWN = [0,1,2,3]

    def __init__(self):
        super().__init__()
        self.state = PEEP_Base.INIT
        self.window_size = 5
        self.transport = None
        self.deserializer = None
        self.base_sequence_number = None
        self.sequence_number = None
        self.acknowledgement = None
        self.window_start = None
        self.window_end = None
        self.data_size = None

    def data_received(self, data):
        # TODO: handle a window of packets
        print("data received")
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            if isinstance(packet, PEEPPacket) and packet.verifyChecksum():
                self.handle_packets(packet)

    def handle_packets(self, packet):
        typenum = packet.Type
        if typenum == PEEPPacket.SYN and self.state == PEEP_Base.INIT:
            print('received SYN')
            self.handle_syn(packet)
        elif typenum == PEEPPacket.SYNACK and self.state == PEEP_Base.HANDSHAKE:
            print('received SYNACK')
            self.handle_synack(packet)
        elif typenum == PEEPPacket.ACK and (self.state == PEEP_Base.TRANS or self.state == PEEP_Base.HANDSHAKE):
            print("received ACK")
            self.handle_ack(packet)
        elif typenum == PEEPPacket.DATA and self.state == PEEP_Base.TRANS:
            print('received Data')
            self.handle_data(packet)
        elif typenum == PEEPPacket.RIP and self.state == PEEP_Base.TRANS:
            print('received RIP')
            self.handle_rip(packet)
        elif typenum == PEEPPacket.RIPACK and self.state == PEEP_Base.TEARDOWN:
            print('received RIPACK')
            self.handle_ripack(packet)
        else:
            print('received UNKNOWN TYPE')

    def handle_syn(self, packet):
        print('checksum of SYN is correct')
        packetback = PEEPPacket()
        packetback.Acknowledgement = packet.SequenceNumber + 1
        packetback.SequenceNumber = random.randint(0,2**16)
        packetback.Type = PEEPPacket.SYNACK
        packetback.updateChecksum()
        self.transport.write(packetback.__serialize__())
        self.state = PEEP_Base.HANDSHAKE
        print('sent SYNACK')

    def handle_synack(self, packet):
        print("Received synack")
        packet_to_send = PEEPPacket()
        packet_to_send.Type = PEEPPacket.ACK
        packet_to_send.SequenceNumber = packet.Acknowledgement
        self.base_sequence_number = packet.Acknowledgement
        self.sequence_number = self.base_sequence_number
        packet_to_send.Acknowledgement= packet.SequenceNumber+1
        packet_to_send.updateChecksum()
        print("Sending Back Ack")
        self.transport.write(packet_to_send.__serialize__())
        self.state = PEEP_Base.TRANS # transmission state
        # Open upper layer transport
        print("connection_made to higher protocol")
        self.higherProtocol().connection_made(PEEP_Transport(self.transport, self))

    def handle_ack(self, packet):
        print("ack: ", packet.Acknowledgement)
        self.window_start = max(self.window_start, packet.Acknowledgement)
        self.window_end = self.window_start + self.window_size * self.chunk_size
        self.send_window_data()

    def handle_data(self, packet):
        self.acknowledgement = packet.SequenceNumber + len(packet.Data)
        ack_packet = PEEPPacket()
        ack_packet.Acknowledgement = self.acknowledgement
        ack_packet.Type = PEEPPacket.ACK
        ack_packet.updateChecksum()
        self.higherProtocol().data_received(packet.Data)
        print("sending ack")
        print("ack: ", self.acknowledgement)
        self.transport.write(ack_packet.__serialize__())
        # TODO: make sure in order

    def handle_rip(self, packet):
        print('checksum of RIP is correct')
        # Sending remaining packets back
        packetback = PEEPPacket()
        self.Acknowledgement = packet.SequenceNumber + 1
        packetback.Acknowledgement = self.Acknowledgemen
        packetback.Type = PEEPPacket.RIPACK
        packetback.updateChecksum()
        self.transport.write(packetback.__serialize__())
        print('sent RIPACK')
        # TODO: send remaining data

    def handle_ripack(self, packet):
        # TODO: send the rest of the data
        packetback = PEEPPacket()
        packetback.Acknowledgement = packet.SequenceNumber + 1
        packetback.Type = PEEPPacket.RIP
        packetback.updateChecksum()
        self.transport.write(packetback.__serialize__())
        print('sent rip pt. 2')
        self.transport.close()

    def transmit_data(self, data, chunk_size):
        # TODO: need to append the data, not remove it.
        # Case: if protocol sends 2 consecutive packets, the 2nd packet
        # will replace the first packet.
        self.data += data
        self.data_size += len(data)
        self.chunk_size = chunk_size
        self.base_sequence_number = self.sequence_number
        self.window_start = self.base_sequence_number
        self.window_end = self.window_start
        print("transmitting data size: ", self.data_size)
        self.send_window_data()

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

    def connection_made(self, transport):
        raise NotImplementedError

    def connection_lost(self, exc):
        self.transport.close()
        self.transport = None

    def initiate_teardown(self):
        # TODO: not sure how to handle the sequence numbers correctly right now
        pass



class PEEP_Transport(StackingTransport):

    def __init__(self, transport, protocol):
        self._lowerTransport = transport
        self.protocol = protocol
        self.transport = self._lowerTransport
        self.chunk_size = 1024

    def write(self, data):
        print("peep transport write")
        self.protocol.data = None
        self.protocol.transmit_data(data, self.chunk_size)

    def close(self):
        self.protocol.initiate_teardown()
