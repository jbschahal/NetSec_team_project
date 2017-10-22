import asyncio
import random
import playground
from .Peep_Packets import PEEPPacket
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
from playground.network.packet import PacketType
from playground.common import Timer, Seconds

class PEEP_Base(StackingProtocol):

    INIT, HANDSHAKE, TRANS, TEARDOWN = [0,1,2,3]

    def __init__(self):
        super().__init__()
        self.state = PEEP_Base.INIT
        self.window_size = 10
        self.transport = None
        self.deserializer = None
        self.base_sequence_number = None
        self.sequence_number = None
        self.acknowledgement = None
        self.send_window_start = None
        self.send_window_end = None
        self.receive_window_start = None
        self.receive_window_end = None
        self.data_size = 0
        self.data = bytes()
        self.timers = []

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
        elif typenum == PEEPPacket.RIP:# and self.state == PEEP_Base.TRANS:
            print('received RIP')
            self.handle_rip(packet)
        elif typenum == PEEPPacket.RIPACK:# and self.state == PEEP_Base.TEARDOWN:
            print('received RIPACK')
            self.handle_ripack(packet)
        else:
            print('received UNKNOWN TYPE')

    def handle_syn(self, packet):
        print('checksum of SYN is correct')
        packetback = PEEPPacket()
        packetback.Acknowledgement = packet.SequenceNumber + 1
        self.sequence_number = random.randint(0, 2**16)
        self.base_sequence_number = self.sequence_number + 1
        self.send_window_start = self.base_sequence_number
        self.send_window_end = self.base_sequence_number
        packetback.SequenceNumber = self.sequence_number
        packetback.Type = PEEPPacket.SYNACK
        packetback.updateChecksum()
        self.send_packet(packetback)
        self.state = PEEP_Base.HANDSHAKE
        print('sent SYNACK')

    def handle_synack(self, packet):
        print("Received synack")
        packet_to_send = PEEPPacket()
        packet_to_send.Type = PEEPPacket.ACK
        packet_to_send.SequenceNumber = packet.Acknowledgement
        self.base_sequence_number = packet.Acknowledgement
        self.send_window_start = self.base_sequence_number
        self.send_window_end = self.base_sequence_number
        self.sequence_number = self.base_sequence_number
        packet_to_send.Acknowledgement= packet.SequenceNumber+1
        packet_to_send.updateChecksum()
        print("Sending Back Ack")
        self.send_packet(packet_to_send)
        self.state = PEEP_Base.TRANS # transmission state
        # Open upper layer transport
        print("connection_made to higher protocol")
        self.higherProtocol().connection_made(PEEP_Transport(self.transport, self))

    def handle_ack(self, packet):
        print("ack: ", packet.Acknowledgement)
        i = 0
        while i < len(self.timers):
            timer = self.timers[i]
            if timer._callbackArgs[0].SequenceNumber < packet.Acknowledgement:
                timer.cancel()
            i += 1
        self.send_window_start = max(self.send_window_start, packet.Acknowledgement)
        self.send_window_end = self.send_window_start + self.window_size * self.chunk_size
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
        self.send_packet(ack_packet)
        # TODO: make sure in order

    def transmit_data(self, data, chunk_size):
        self.data += data
        self.data_size += len(data)
        self.chunk_size = chunk_size
        print("transmitting data size: ", self.data_size)
        self.send_window_data()

    def send_window_data(self):
        print('send window data')
        while self.send_window_end - self.send_window_start <= self.window_size * self.chunk_size:
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
        packet.Data = self.data[i:min(i+self.chunk_size, self.send_window_start + self.window_size * self.chunk_size)]
        packet.updateChecksum()
        print("sending: " , packet.SequenceNumber)
        self.send_packet(packet)
        self.sequence_number += len(packet.Data)
        self.send_window_end += len(packet.Data)

    def connection_made(self, transport):
        raise NotImplementedError

    def connection_lost(self, exc):
        self.transport.close()
        self.transport = None
        asyncio.get_event_loop().stop()

    def send_packet(self, packet):
        self.transport.write(packet.__serialize__())
        if packet.Type != PEEPPacket.SYN or packet.Type != PEEPPacket.DATA:
            return
        timer = Timer(Seconds(1), self.send_packet, packet)
        self.timers.append(timer)
        timer.start()

    def clear_data_buffer(self):
        while self.sequence_number - self.base_sequence_number < self.data_size:
            self.send_window_data()
        rip2 = PEEPPacket(Type=PEEPPacket.RIP)
        rip2.SequenceNumber = self.sequence_number
        rip2.updateChecksum()
        self.send_packet(rip2)

    def initiate_teardown(self):
        rip = PEEPPacket(Type=PEEPPacket.RIP)
        rip.SequenceNumber = self.sequence_number
        self.sequence_number += 1
        rip.updateChecksum()
        self.state = PEEP_Base.TEARDOWN
        print("sent first rip")
        self.send_packet(rip)
        self.handle_rip = self.handle_second_rip
        pass

    def handle_second_rip(self, packet):
        ripack = PEEPPacket(Type=PEEPPacket.RIPACK)
        ripack.SequenceNumber = self.sequence_number
        ripack.updateChecksum()
        self.send_packet(ripack)
        self.transport.close()

    def handle_second_ripack(self, packet):
        self.transport.close()

    def handle_rip(self, packet):
        print('checksum of RIP is correct')
        # Sending remaining packets back
        self.handle_ripack = self.handle_second_ripack
        packetback = PEEPPacket()
        self.Acknowledgement = packet.SequenceNumber + 1
        packetback.Acknowledgement = self.Acknowledgement
        packetback.Type = PEEPPacket.RIPACK
        packetback.updateChecksum()
        print('sent RIPACK')
        self.send_packet(packetback)
        self.clear_data_buffer()
        self.state = PEEP_Base.TEARDOWN
        packetback = PEEPPacket()
        packetback.Type = PEEPPacket.RIP
        packetback.SequenceNumber = self.sequence_number
        packetback.updateChecksum()
        self.send_packet(packetback)
        # self.transport.close()

    def handle_ripack(self, packet):
        # TODO: send the rest of the data
        self.handle_ack(packet)



class PEEP_Transport(StackingTransport):

    def __init__(self, transport, protocol):
        super().__init__(transport)
        self._lowerTransport = transport
        self.protocol = protocol
        self.transport = self._lowerTransport
        self.chunk_size = 1024

    def write(self, data):
        print("peep transport write")
        self.protocol.transmit_data(data, self.chunk_size)

    def close(self):
        self.protocol.initiate_teardown()
