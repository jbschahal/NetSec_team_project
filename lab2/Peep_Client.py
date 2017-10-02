import asyncio
import random
import playground
from Peep_Packets import PEEP_Packet
from playground.network.packet import PacketType
from PassingThroughProtocols import FirstPassingThroughProtocol, SecondPassingThroughProtocol
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory

class PEEP_Client(StackingProtocol):
    def __init__(self):
        self.transport = None
        self.state = 0
        self.deserializer = None
        self.higherProtocolConnectionMade = False
        super().__init__

    def data_received(self, data):
        if self.state == 1:
            # expecting a synack
            self.deserializer.update(data)
            for packet in self.deserializer.nextPackets():
                if isinstance(packet, PEEP_Packet):
                    if (packet.Type == 1):
                        # received a synack
                        if (packet.verifyChecksum()):
                            higherTransport = StackingTransport(self.transport)
                            self.higherProtocol().connection_made(higherTransport)
                            self.higherProtocolConnectionMade = True

                            if packet.Acknowledgement == self.sequence_number + 1:
                                print("Received synack")
                                print("connection_made to higher protocol: Middle layer")
                                print("Sending Back Ack")
                                packet_to_send = PEEP_Packet()
                                packet_to_send.Type = 2
                                packet_to_send.SequenceNumber = packet.Acknowledgement
                                packet_to_send.Acknowledgement= packet.SequenceNumber+1
                                packet_to_send.updateChecksum()
                                self.transport.write(packet_to_send.__serialize__())
                                self.state = 2 # transmission state
        elif self.state == 2:
            #expecting a message packet
            print("Message data received")
            self.higherProtocol().data_received(data)

    def connection_made(self, transport):
        self.transport = transport
        self.deserializer = PacketType.Deserializer()
        self.start_handshake()
        if self.higherProtocolConnectionMade == True:
            self.higherProtocol().data_received(data)

    def connection_lost(self, exc):
        self.transport = None 
        if self.higherProtocolConnectionMade == True:
            self.higherProtocol().connection_lost(exc)

    def start_handshake(self):
        self.sequence_number = random.randint(0,1000)
        print("Client start handshake")
        packet = PEEP_Packet()
        packet.Type = self.state
        packet.SequenceNumber = self.sequence_number
        packet.updateChecksum()
        self.transport.write(packet.__serialize__())
        self.state = 1

loop = asyncio.get_event_loop()
loop.set_debug(enabled=True)
# Chains two layers together
f = StackingProtocolFactory(lambda: FirstPassingThroughProtocol(), lambda: PEEP_Client())
ptConnector = playground.Connector(protocolStack=f)
playground.setConnector("passthrough", ptConnector)
coro = playground.getConnector('passthrough').create_playground_connection(lambda: SecondPassingThroughProtocol(), '20174.1.1.1', 888)
transport, c = loop.run_until_complete(coro)
loop.run_forever()
