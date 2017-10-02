# two layers of passing through protocols
import asyncio
import logging
import playground
from playground.network.common import StackingProtocol, StackingTransport, StackingProtocolFactory
# initialize logger
logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger()
logger.setLevel(logging.NOTSET)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Layer 1
class FirstPassingThroughProtocol(StackingProtocol):
    def __init__(self):
        logging.info('FirstPassingThroughProtocol initialized')
        print('PRINT - FirstPassingThroughProtocol initialized')
        print('')
        self.transport = None
        super().__init__

    def connection_made(self, transport):
        logging.info('FirstPassingThroughProtocol connection made')
        print('PRINT - FirstPassingThroughProtocol connection made')
        print('')
        self.transport = transport
        higherTransport = StackingTransport(self.transport)
        self.higherProtocol().connection_made(higherTransport)

    def data_received(self, data):
        logging.info('FirstPassingThroughProtocol data received')
        print('PRINT - FirstPassingThroughProtocol data received')
        print('')
        self.higherProtocol().data_received(data)

    def connection_lost(self, exc):
        logging.info('FirstPassingThroughProtocol connection lost')
        print('PRINT - FirstPassingThroughProtocol connection lost')
        print('')
        self.transport = None
        self.higherProtocol().connection_lost(exc)

# Layer 2
class SecondPassingThroughProtocol(asyncio.Protocol):
    def __init__(self):
        logging.info('SecondPassingThroughProtocol initialized')
        print('PRINT - SecondPassingThroughProtocol initialized')
        print('')
        self.transport = None

    def connection_made(self, transport):
        logging.info('SecondPassingThroughProtocol connection made')
        print('PRINT - SecondPassingThroughProtocol connection made')
        print('')
        self.transport = transport

    def data_received(self, data):
        logging.info('SecondPassingThroughProtocol data received')
        print('PRINT - SecondPassingThroughProtocol data received')
        print('')

    def connection_lost(self, exc):
        logging.info('SecondPassingThroughProtocol connection lost')
        print('PRINT - SecondPassingThroughProtocol connection lost')
        print('')
        self.transport = None