import playground
from .Peep_Passthrough import clientFactory, serverFactory

lab2Connector = playground.Connector(protocolStack = (clientFactory, serverFactory))
playground.setConnector("lab2_protocoltest", lab2Connector)
