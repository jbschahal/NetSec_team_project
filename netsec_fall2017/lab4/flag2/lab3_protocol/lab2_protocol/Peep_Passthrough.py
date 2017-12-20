import asyncio
import random
import playground
from .Peep_Packets import PEEPPacket
from .Peep_Base import PEEP_Base, PEEP_Transport
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
from playground.network.packet import PacketType

class PEEP_Client(PEEP_Base):

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

    def connection_made(self, transport):
        self.transport = transport
        self.deserializer = PEEPPacket.Deserializer()
        self.start_handshake()

    def handle_syn(self, packet):
        raise Exception("I received a SYN packet when I never should")

    def start_handshake(self):
        print("-----------PEEP Start Handshake-----------")
        self.sequence_number = random.randint(0,2**16)
        # print("peep_client: start handshake")
        packet = PEEPPacket()
        packet.Type = PEEPPacket.SYN
        packet.Data = "piggyback".encode()
        packet.SequenceNumber = self.sequence_number
        packet.updateChecksum()
        self.send_packet(packet)
        self.sequence_number += 1
        self.state = PEEP_Client.HANDSHAKE

class PEEP_Server(PEEP_Base):

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

    def connection_made(self,transport):
        # print("peep_server: connection made")
        self.transport = transport
        self.higherProtocol().transport = PEEP_Transport(transport, self)
        self.deserializer = PEEPPacket.Deserializer()

    def handle_synack(self, packet):
        raise Exception("I received a SYN packet when I never should")

    def handle_ack(self,packet):
        if self.state == PEEP_Server.HANDSHAKE:
                # print('peep_server: handshake is complete')
                # print("ack: ", packet.Acknowledgement)
                # send data
                self.state = PEEP_Server.TRANS
                self.sequence_number = packet.Acknowledgement
                self.base_sequence_number = self.sequence_number
                # open upper layer transport
                self.higherProtocol().connection_made(PEEP_Transport(self.transport, self))
        else:
            super().handle_ack(packet)


clientFactory = StackingProtocolFactory(PEEP_Client)
serverFactory = StackingProtocolFactory(PEEP_Server)
