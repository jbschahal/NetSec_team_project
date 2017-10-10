"""
A protocol for a random number generator game. Packet is defined
in packet.py

- Client connects to server
- Server generates a random number and sends a range that
  number lies in to the client.
- The client will then respond with a guess.
- If that guess is correct, then the server will say so. Otherwise,
  it will say incorrect.

Created by chengsteven on 9/4/2017
"""

import asyncio
import random
from RNG_game_packets import RequestRandomNumberPacket, RandomNumberProblemPacket,\
    GuessPacket, CorrectnessPacket
from playground.network.packet import PacketType
#from playground.common import logging as p_logging
#p_logging.EnablePresetLogging(p_logging.PRESET_TEST)


class RandomNumberGameServerProtocol(asyncio.Protocol):

    _ID = 0

    def __init__(self, seed=None):
        self.transport = None
        self.Deserializer = None
        self.number = seed
        self.game_id = self._ID; RandomNumberGameServerProtocol._ID+=1
        # Here, we define states:
        # 0 - expecting RandomNumberProblemPacket
        # 1 - expecting GuessPacket
        # 2 - Done, expecting nothing
        self.state = 0

    def connection_made(self, transport):
        print("Client has been connected to server.")
        self.transport = transport
        self.Deserializer = PacketType.Deserializer()

    def connection_lost(self, exc):
        self.transport = None

    def data_received(self, data):
        print("rng server data rec")
        self.Deserializer.update(data)
        for packet in self.Deserializer.nextPackets():
            print("rng server packet: ", packet)
            if isinstance(packet, RequestRandomNumberPacket) and self.state == 0:
                # send a RandomNumberProblemPacket
                if (not self.number):
                    self.number = random.randint(1, 10)
                self.state+=1
                print("rng server problem packet")
                self.transport.write(RandomNumberProblemPacket(min_range=1, max_range=10, game_id=self.game_id).__serialize__())
            elif isinstance(packet, GuessPacket) and self.state == 1:
                self.state+=1
                if packet.guess == self.number:
                    # correct guess
                    print("rng server correctness packet")
                    self.transport.write(CorrectnessPacket(game_id=self.game_id, correct=True).__serialize__())
                else:
                    # incorrect guess
                    print("rng server correctness packet")
                    self.transport.write(CorrectnessPacket(game_id=self.game_id, correct=False).__serialize__())
            else:
                self.transport.close()

    def eof_received(self):
        return None

class RandomNumberGameClientProtocol(asyncio.Protocol):

    def __init__(self, loop):
        self.transport = None
        self.Deserializer = None
        self.game_id = None
        self.loop = loop
        self.guess = None
        # Defining states
        # 0 - beginning state, not yet sent a request to start the game
        # 1 - expecting the RandomNumberProblemPacket
        # 2 - expecting CorrectnessPacket
        # 3 - Done, expecting nothing
        self.state = 0

    def connection_made(self, transport):
        print("Server has connected to the client")
        self.transport = transport
        self.Deserializer = PacketType.Deserializer()
        self.initiate_game(random.randint(0,9))
        # send a game request

    def connection_lost(self, exc):
        self.transport = None
        self.loop.stop()

    def data_received(self, data):
        print("rng client data rec")
        self.Deserializer.update(data)
        for packet in self.Deserializer.nextPackets():
            print("rng cli packet: ", packet)
            if isinstance(packet, RandomNumberProblemPacket) and self.state == 1:
                # we received a game packet, print the range and ask
                # for input
                self.game_id = packet.game_id
                print("Guessing: " + str(self.guess))
                self.state+=1
                print("rng client guess packet")
                self.transport.write(GuessPacket(game_id=self.game_id, guess=self.guess).__serialize__())
            elif isinstance(packet, CorrectnessPacket) and self.state == 2:
                # state whether you were correct.
                # if correct, close session
                # if wrong, ask for another guess
                if packet.correct:
                    print("Correct! You win.")
                else:
                    print("You've guessed incorrectly. Try again.")
                self.state+=1
                self.end_connection()
            else:
                self.end_connection()

    def eof_received(self):
        return None

    def end_connection(self):
        self.transport.close()
        self.loop.stop()

    def initiate_game(self, guess):
        if (self.state != 0): self.transport.close()
        self.guess = guess
        self.state+=1
        self.transport.write(RequestRandomNumberPacket().__serialize__())


def basicUnitTest():
    from playground.asyncio_lib.testing import TestLoopEx
    from playground.network.testing import MockTransportToProtocol

    loop = asyncio.get_event_loop()
    print("Making the server choose a 'random' number of 5.")

    client_1 = RandomNumberGameClientProtocol(loop)
    server_1 = RandomNumberGameServerProtocol(seed=5)
    cTransport, sTransport = MockTransportToProtocol.CreateTransportPair(client_1, server_1)
    server_1.connection_made(sTransport)
    client_1.connection_made(cTransport)

    client_1.initiate_game(guess=4)


    client_2 = RandomNumberGameClientProtocol(loop)
    server_2 = RandomNumberGameServerProtocol(seed=5)
    cTransport, sTransport = MockTransportToProtocol.CreateTransportPair(client_2, server_2)
    server_2.connection_made(sTransport)
    client_2.connection_made(cTransport)

    client_2.initiate_game(guess=5)


if __name__ == "__main__":
    basicUnitTest()
    print("Basic unit test completed successfully.")
