import playground
import asyncio
import lab3_protocol
from playground.common import logging as p_logging
p_logging.EnablePresetLogging(p_logging.PRESET_TEST)

class flag3(asyncio.Protocol):
    def __init__(self):
        self.transport=None
    def connection_made(self,transport):
        self.transport = transport
        self.close()
    def close(self):
        self.transport.close()
    def data_received(self,data):
        self.close()




if __name__=='__main__':
    loop = asyncio.get_event_loop()
    coro = playground.getConnector("pls3").create_playground_connection(flag3,"20174.1.1337.3",1)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()

