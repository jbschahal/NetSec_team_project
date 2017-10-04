import asyncio
import playground
import sys
from submission import PassThrough1, PassThrough2
from RNG_game_protocol import RandomNumberGameServerProtocol,\
    RandomNumberGameClientProtocol
from playground.network.common import StackingProtocolFactory

USAGE = """usage: <mode>
  mode is either 'server' or 'client as a.b.c.d playground address'"""

if __name__ == "__main__":

    f = StackingProtocolFactory(PassThrough1, PassThrough2)
    ptConnector = playground.Connector(protocolStack = f)
    playground.setConnector("passThrough", ptConnector)
    args = sys.argv[1:]

    if len(args) != 1:
        print(USAGE)
    elif args[0] == 'server':
        loop = asyncio.get_event_loop()
        coro = playground.getConnector("passThrough").create_playground_server(RandomNumberGameServerProtocol,
                                    8888)
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
        loop = asyncio.get_event_loop()
        coro = playground.getConnector("passThrough").create_playground_connection(lambda: RandomNumberGameClientProtocol(loop),
                                    args[0], 8888)
        socket, rng_client_proto = loop.run_until_complete(coro)
        guess = int(input("Enter a number between 1-10: "))
        rng_client_proto.initiate_game(guess)
        loop.run_forever()
