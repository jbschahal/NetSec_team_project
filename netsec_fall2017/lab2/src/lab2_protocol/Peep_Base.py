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
        self.chunk_size = 1024
        self.transport = None
        self.deserializer = None
        self.base_sequence_number = None
        self.sequence_number = None
        self.expected_sequence_number = None
        self.send_window_start = None
        self.send_window_end = None
        self.receive_window_start = None
        self.receive_window_end = None
        self.data_size = 0
        self.data = bytes()
        self.timers = []
        self.received_data = []
        self.rip_timer = None
        self.rip_sequence_number = None

    def data_received(self, data):
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
        elif typenum == PEEPPacket.ACK:
            print("received ACK")
            self.handle_ack(packet)
        elif typenum == PEEPPacket.DATA and (self.state == PEEP_Base.TRANS or self.state == PEEP_Base.TEARDOWN):
            print('received Data')
            self.handle_data(packet)
        elif typenum == PEEPPacket.RIP and (self.state == PEEP_Base.TRANS or self.state == PEEP_Base.TEARDOWN):
            print('received RIP')
            self.handle_rip(packet)
        elif typenum == PEEPPacket.RIPACK and self.state == PEEP_Base.TEARDOWN:
            print('received RIPACK')
            self.handle_ripack(packet)
        else:
            print('received packet in bad state. type: ', typenum, " state ", self.state)

    def handle_syn(self, packet):
        print('checksum of SYN is correct')
        packetback = PEEPPacket()
        packetback.Acknowledgement = packet.SequenceNumber + 1
        self.sequence_number = random.randint(0, 2**16)
        self.base_sequence_number = self.sequence_number + 1
        self.expected_sequence_number = packet.SequenceNumber + 1
        self.send_window_start = self.base_sequence_number
        self.send_window_end = self.base_sequence_number
        packetback.SequenceNumber = self.sequence_number
        packetback.Type = PEEPPacket.SYNACK
        packetback.updateChecksum()
        self.send_packet(packetback)
        self.state = PEEP_Base.HANDSHAKE
        # maybe set this state to trans in case the ack in handshake gets dropped
        print('sent SYNACK')

    def handle_synack(self, packet):
        print("Received synack")
        packet_to_send = PEEPPacket()
        packet_to_send.Type = PEEPPacket.ACK
        packet_to_send.SequenceNumber = packet.Acknowledgement
        packet_to_send.Acknowledgement= packet.SequenceNumber+1
        packet_to_send.updateChecksum()
        self.base_sequence_number = packet.Acknowledgement
        self.expected_sequence_number = packet.SequenceNumber + 1
        self.send_window_start = self.base_sequence_number
        self.send_window_end = self.base_sequence_number
        self.sequence_number = self.base_sequence_number
        print("Sending Back Ack")
        self.send_packet(packet_to_send)
        self.state = PEEP_Base.TRANS # transmission state
        # Open upper layer transport
        print("connection_made to higher protocol")
        self.higherProtocol().connection_made(PEEP_Transport(self.transport, self))

    def handle_ack(self, packet):
        # TODO: sequence number overflow
        print("ack: ", packet.Acknowledgement)
        i = 0
        while i < len(self.timers):
            timer = self.timers[i]
            if timer._callbackArgs[0].SequenceNumber < packet.Acknowledgement:
                timer.cancel()
                self.timers = self.timers[:i] + self.timers[i+1:]
                i -= 1
            i += 1

        if self.rip_timer != None:
            self.rip_timer.cancel()
            self.rip_timer.extend(Seconds(2))
            self.rip_timer.start()
            return

        self.send_window_start = max(self.send_window_start, packet.Acknowledgement)
        self.send_window_data()

        if self.state == PEEP_Base.TEARDOWN and self.sent_all():
            self.send_rip()
            self.rip_timer = Timer(Seconds(2), self.abort_connection)
            self.rip_timer.start()

    def handle_data(self, packet):
        self.received_data.append(packet)
        if packet.SequenceNumber == self.expected_sequence_number:
            self.pass_data_up()

        ack_packet = PEEPPacket()
        ack_packet.Acknowledgement = self.expected_sequence_number
        ack_packet.Type = PEEPPacket.ACK
        ack_packet.updateChecksum()
        print("sending ack")
        print("ack: ", self.expected_sequence_number)
        self.send_packet(ack_packet)

        if self.state == PEEP_Base.TEARDOWN and self.received_all():
            self.send_rip_ack(self.rip_sequence_number + 1)

    def pass_data_up(self):
        self.received_data.sort(key = lambda packet: packet.SequenceNumber)
        i = 0
        while i < len(self.received_data):
            packet = self.received_data[i]
            if packet.SequenceNumber == self.expected_sequence_number:
                self.higherProtocol().data_received(packet.Data)
                self.expected_sequence_number += len(packet.Data)
                self.received_data = self.received_data[:i] + self.received_data[i+1:]
                i -= 1
            i += 1

    def transmit_data(self, data):
        self.data += data
        self.data_size += len(data)
        print("transmitting data size: ", self.data_size)
        self.send_window_data()

    def send_window_data(self):
        print('send window data')
        while self.send_window_end - self.send_window_start < self.window_size * self.chunk_size:
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
        print(self, "send packet: ", packet)
        self.transport.write(packet.__serialize__())
        if packet.Type != PEEPPacket.SYN and packet.Type != PEEPPacket.DATA and packet.Type != PEEPPacket.RIP:
            return
        timer = Timer(Seconds(1), self.send_packet, packet)
        self.timers.append(timer)
        timer.start()

    def initiate_teardown(self):
        print('teardown start')
        self.state = PEEP_Base.TEARDOWN
        if self.sent_all():
            self.send_rip()
            self.rip_timer = Timer(Seconds(2), self.abort_connection)
            self.rip_timer.start()

    def received_all(self):
        return self.rip_sequence_number == self.expected_sequence_number

    def sent_all(self):
        return self.sequence_number - self.base_sequence_number >= self.data_size

    def handle_rip(self, packet):
        self.state = PEEP_Base.TEARDOWN
        self.rip_sequence_number = packet.SequenceNumber
        if self.received_all():
            self.send_rip_ack(self.rip_sequence_number + 1)

    def send_rip(self):
        print("send rip :", self)
        rip = PEEPPacket(Type=PEEPPacket.RIP)
        rip.SequenceNumber = self.sequence_number
        self.sequence_number += 1
        rip.updateChecksum()
        self.send_packet(rip)

    def send_rip_ack(self, ack):
        ripack = PEEPPacket(Type=PEEPPacket.RIPACK)
        ripack.Acknowledgement = ack
        ripack.updateChecksum()
        self.send_packet(ripack)

    def handle_ripack(self, packet):
        self.transport.close()

    def abort_connection(self):
        self.transport.close()



class PEEP_Transport(StackingTransport):

    def __init__(self, transport, protocol):
        super().__init__(transport)
        self._lowerTransport = transport
        self.protocol = protocol
        self.transport = self._lowerTransport

    def write(self, data):
        print("peep transport write")
        self.protocol.transmit_data(data)

    def close(self):
        self.protocol.initiate_teardown()

    def abort(self):
        self.protocol.abort_connection()
