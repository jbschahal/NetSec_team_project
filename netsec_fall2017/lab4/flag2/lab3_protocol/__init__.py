import playground
from .PLS_Passthrough import clientFactory, serverFactory

lab3Connector = playground.Connector(protocolStack = (clientFactory, serverFactory))
playground.setConnector("pls", lab3Connector)
