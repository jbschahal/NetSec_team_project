import asyncio
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, STRING
from peep_packets import PEEP_Packet
from random import randint

class ServerProtocol(asyncio.Protocol):
	def __init__(self):
		self.received=0
		self.transport=None
		self._Deserializer = PacketType.Deserializer()
		self.state=0

	def connection_made(self,transport):
		self.transport=transport
		self._Deserializer=PacketType.Deserializer()
		peername = transport.get_extra_info('peername')
		print('server(prepare)-->client(prepare):Connection from {}'.format(peername))

	def data_received(self,data):
		self._Deserializer=PacketType.Deserializer()
		self._Deserializer.update(data)
		for pkt in self._Deserializer.nextPackets():
			self.handle_packets(pkt)

	def handle_packets(self,pkt):
		if isinstance(pkt,PEEP_Packet):
			typenum = pkt.Type
			if typenum == 0 and self.state == 0:
				print('server side: received SYN')
				self.handle_syn(pkt)
			elif typenum == 2 and self.state == 1:
				print('server side: received ACK')
				self.handle_ack(pkt)
			elif typenum == 3 and self.state == 2:
				print('server side: received RIP')
				self.handle_rip(pkt)
			elif typenum == 4 and self.state == 2:
				print('server side: received RIPACK')
				self.handle_ripack(pkt)
			else:
				print('server side: received UNKNOWN TYPE')
		else:
			print('server side:This packet is not the correct type')
	def handle_syn(self,pkt):
		if pkt.Checksum == 0:
			print('server side: checksum of SYN is correct')
			pktback=PEEP_Packet()
			pktback.Acknowledgement=pkt.SequenceNumber+1
			pktback.SequenceNumber = randint(0,100)
			pktback.Type=1
			pktback.Checksum=0
			self.transport.write(pktback.__serialize__())
			self.state+=1
			print('server side: sent SYNACK')
		else:
			print('server side: checksum of SYN is incorrect')
			pktback=PEEP_Packet()
			pktback.Type=5
			pktback.Checksum=0
			self.transport.write(pktback.__serialize__())
			print('server side: sent RST')
			# clear buffer
			self.transport.close()
		
	def handle_ack(self,pkt):
		if pkt.Checksum == 0:
			print('server side: checksum of ACK is correct')
			#send data
			self.state+=1
			
		else:
			print('server side: checksum of ACK is incorrect')
			pktback=PEEP_Packet()
			pktback.Type=5
			pktback.Checksum=0
			self.transport.write(pktback.__serialize__())
			self.transport.close()
			print('server side: sent RST')

	def handle_rip(self,pkt):
		if pkt.Checksum == 0:
			print('server side: checksum of RIP is correct')
			pktback=PEEP_Packet()
			pktback.Acknowledgement=pkt.SequenceNumber+1
			pktback.Type=4
			pktback.Checksum=0
			self.transport.write(pktback.__serialize__())
			print('server side: sent RIPACK')
			# Sending remaining packets back
			pktback2=PEEP_Packet()
			pktback2.Acknowledgement=pkt.SequenceNumber+1
			pktback2.Type=3
			pktback2.Checksum=0
			pktback2.SequenceNumber=randint(0,100)
			self.transport.write(pktback2.__serialize__())
			print('server side: sent RIP')
		else:
			print('server side: checksum of RIP is incorrect')
			pktback=PEEP_Packet()
			pktback.Type=5
			pktback.Checksum=0
			self.transport.write(pktback.__serialize__())
			self.transport.close()
			print('server side: sent RST')

	def handle_ripack(self,pkt):
		if pkt.Checksum == 0:
			print('server side: checksum of RIPACK is correct')
			self.transport.close()
		else:
			print('server side: checksum of RIPACK is incorrect')
			self.transport.close()

loop = asyncio.get_event_loop()
# Each client connection will create a new protocol instance
coro = loop.create_server(ServerProtocol, '127.0.0.1', 9997)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass


# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()


		
