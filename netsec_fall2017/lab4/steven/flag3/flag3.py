import sys
import asyncio
import playground
from lab3_protocol.Mobile_Packets import *
# from playground.common import logging as p_logging
# p_logging.EnablePresetLogging(p_logging.PRESET_TEST)

USAGE = """usage: flag2 <server address> <port>"""

"""
Goal:

Connect to a mobile code server that checks certs badly.

Steps:

Find the right server.
    try handshaking each server multiple times
    see what's being received
Find the right cert vulnerability.
    try to check ip_subset
    see if any duplicate packet fields are being used

TODO:
    import mobileservice packets to send to the server and get responses
    must be able to be decrypted
"""


class flag3(asyncio.Protocol):

    def __init__(self):
        self.transport = None
        self.deserializer = None

    def connection_made(self, transport):
        print("-----------flag3 Connection Made----------- ")
        self.transport = transport
        #return
        test_packet = OpenSession()
        test_packet.Cookie = 10
        print("send open session with cookie ", test_packet.Cookie)
        self.transport.write(test_packet.__serialize__())

    def data_received(self, data):
        self.deserializer = MobileCodePacket.Deserializer()
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            if isinstance(packet, MobileCodeServiceDiscoveryResponse):
                print("----------------------flag3 MCS Discovery Response----------------------")
                print("Address: ", packet.Address)
                print("Port: ", packet.Port)
                print("Traits: ", packet.Traits)
            elif isinstance(packet, OpenSessionResponse):
                print("----------------------flag3 Open Session Response----------------------")
                print("Cookie: ", packet.Cookie)
                print("WalletId: ", packet.WalletId)
                print("AuthId: ", packet.AuthId)
                print("EngineId: ", packet.EngineId)
                print("NegotiationAttributes: ", packet.NegotiationAttributes)
            else:
                print("------flag3 different packet------")
                print(packet)


    def connection_lost(self, error):
        pass


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 2:
        print(USAGE)
    else:
        loop = asyncio.get_event_loop()
        loop.set_debug(enabled=True)
        coro = playground.getConnector("flag3").create_playground_connection(
            flag3, args[0], int(args[1]))
        socket, client_proto = loop.run_until_complete(coro)
        loop.run_forever()
