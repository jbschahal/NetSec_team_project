import sys
import asyncio
import playground
from playground.network.common import StackingProtocol

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
"""


class flag2(asyncio.Protocol):

    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        print("-----------FLAG2 Connection Made----------- ")
        self.transport = transport

    def data_received(self, data):
        print("Data received", data)

    def connection_lost(self, error):
        pass


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 2:
        print(USAGE)
    else:
        loop = asyncio.get_event_loop()
        loop.set_debug(enabled=True)
        coro = playground.getConnector("pls").create_playground_connection(flag2, args[0], int(args[1]))
        print(coro)
        socket, client_proto = loop.run_until_complete(coro)
        loop.run_forever()
