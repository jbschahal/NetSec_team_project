import playground
import os
from MobileCodeService.Packets import MobileCodePacket
import logging
import asyncio
import ParallelTSP_mobile
import lab3_protocol
import sys

class flag5(asyncio.Protocol):
    def __init__(self):
        self.tranport = None
        self.deserializer = MobileCodePacket.Deserializer()
        self.code = None
    def connection_made(self,transport):
        self.tranport = transport
        packet = OpenSession()
        pakcet.Cookie = 100
        self.transport.write(packet.__serialize__())




    def data_received(self,data):
        self.deserializer.update(data)
        for pkt in deserializer.nextPackets():
            if isinstance(pkt,OpenSessionResponse):
                packet_back = RunMobileCode()
                packet_back.Cookie = 100
                with open("ParallelTSP_mobile") as file:
                    self.code = file.read()
                print(self.code)

                packet_back.Code = self.code
                self.tranport.write(packet_back.__serialize__())


loop = asyncio.get_event_loop()
loop.set_debug(enabled = True)
coro = playground.getConnector("plsmobile").create_playground_connection(flag5, "20174.1.1337.3",1)
socket,pro = loop.run_until_complete(coro)
loop.run_forever()
loop.close()


