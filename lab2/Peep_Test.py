import asyncio
import playground
import sys
from playground.network.common import StackingProtocolFactory
from Peep_Passthrough import PEEP_1a, PEEP_1b
from RNG_game_protocol import RandomNumberGameServerProtocol, RandomNumberGameClientProtocol

USAGE = """usage: Peep_Protocol <mode>
  mode is either 'server' or 'client as a.b.c.d playground address'"""

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print(USAGE)
    elif args[0] == 'server':
        f = StackingProtocolFactory(PEEP_1b)
        ptConnector = playground.Connector(protocolStack=f)
        playground.setConnector("server_pt", ptConnector)

        loop = asyncio.get_event_loop()
        loop.set_debug(enabled=True)
        coro = playground.getConnector("server_pt").create_playground_server(RandomNumberGameServerProtocol, 8888)

        server = loop.run_until_complete(coro)

        # Server until Crtl-C is hit
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()
    else:
        f = StackingProtocolFactory(PEEP_1a)
        ptConnector = playground.Connector(protocolStack=f)
        playground.setConnector("client_pt", ptConnector)

        loop = asyncio.get_event_loop()
        loop.set_debug(enabled=True)
        coro = playground.getConnector("client_pt").create_playground_connection(lambda: RandomNumberGameClientProtocol(loop), args[0], 8888)

        socket, client_proto = loop.run_until_complete(coro)
        loop.run_forever()
