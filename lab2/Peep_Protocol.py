import asyncio
import playground
import sys
from Peep_Server import PEEP_Server
from Peep_Client import PEEP_Client

USAGE = """usage: Peep_Protocol <mode>
  mode is either 'server' or 'client as a.b.c.d playground address'"""

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print(USAGE)
    elif args[0] == 'server':
        f = StackingProtocolFactory(lambda: PEEP_Server_Passthrough2(), lambda: PEEP_Server_Passthrough1()) ## Higher --> Lower. Can be any number of leyers greater than 1
        ptConnector = playground.Connector(protocolStack=f)
        playground.setConnector("Server_Passthrough", ptConnector)
    
        loop = asyncio.get_event_loop()
        loop.set_debug(enabled=True)
        coro = playground.getConnector("Server_Passthrough").create_playground_server(lambda: PEEP_Client(), 8000)
    
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
        f = StackingProtocolFactory(lambda: PEEP_Passthrough2(), lambda: PEEP_Passthrough1()) ## Higher --> Lower. Can be any number of leyers greater than 1
        ptConnector = playground.Connector(protocolStack=f)
        playground.setConnector("Client_Passthrough", ptConnector)
    
        loop = asyncio.get_event_loop()
        loop.set_debug(enabled=True)
        coro = playground.getConnector("Client_Passthrough").create_playground_server(lambda: PEEP_Client, args[0], 8888)

        socket, client_proto = loop.run_until_complete(coro)
        client_proto.start_handshake()
        loop.run_forever()

