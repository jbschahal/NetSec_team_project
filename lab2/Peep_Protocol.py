import asyncio
import playground
import sys
from Peep_Server import ServerProtocol
from Peep_Client import Peep_Client

USAGE = """usage: echotest <mode>
  mode is either 'server' or 'client as a.b.c.d playground address'"""

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print(USAGE)
    elif args[0] == 'server':
        loop = asyncio.get_event_loop()
        coro = playground.getConnector().create_playground_server(ServerProtocol,
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
        coro = playground.getConnector().create_playground_connection(Peep_Client,
                                    args[0], 8888)
        socket, client_proto = loop.run_until_complete(coro)
        client_proto.start_handshake()
        loop.run_forever()

