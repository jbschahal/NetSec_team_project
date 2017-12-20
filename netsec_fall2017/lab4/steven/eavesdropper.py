import playground
import asyncio
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
# from playground.common import logging as p_logging
# p_logging.EnablePresetLogging(p_logging.PRESET_TEST)


class Demux(StackingProtocol):
    def connectionMade(self):
        pass

    def demux(src, srcPort, dst, dstPort, demuxData):
        print("Packet from ", src, ":", srcPort, ". Going to ", dst, ":", dstPort)
        print("Data: ", demuxData)

eavesdrop = playground.network.protocols.switching.PlaygroundSwitchTxProtocol(Demux, "20174.*.*.*")
coro = asyncio.get_event_loop().create_connection(lambda: eavesdrop, "192.168.200.240", 9090)
loop = asyncio.get_event_loop()
socket, client_proto = loop.run_until_complete(coro)
loop.run_forever()
