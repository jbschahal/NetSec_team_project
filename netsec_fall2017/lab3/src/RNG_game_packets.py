"""
Assignment #1b

Created by chengsteven on 9/4/2017

These packets are used for the rng_guessing protocol. A client will
request a random number guessing problem. The server will send the range
in which the number lies in to the client. The client will then attempt to
guess the number and the server will respond with whether the guess
was correct or not.
"""

from playground.network.packet import PacketType, FIELD_NOT_SET
from playground.network.packet.fieldtypes import UINT8, UINT16, UINT32, UINT64, \
                                                 STRING, BUFFER, BOOL,\
                                                 ComplexFieldType, PacketFields
from playground.network.packet.fieldtypes.attributes import Optional

class RequestRandomNumberPacket(PacketType):
    """
    The client will send this packet to the server to initiate
    a RNG Guess problem. The server will then generate a random
    number, remember the number, and send the range in which the
    number lies in for the client to guess
    *default range is [1-10]
    """
    DEFINITION_IDENTIFIER = "rng_guessing.RequestRandomNumberPacket"
    DEFINITION_VERSION = "1.0"
    FIELDS = []

class RandomNumberProblemPacket(PacketType):
    """
    This packet is sent by the server after receiving a problem request
    from the client.
    """
    DEFINITION_IDENTIFIER = "rng_guessing.RandomNumberProblemPacket"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("min_range", UINT16),
        ("max_range", UINT16),
        ("game_id", UINT16)
    ]

class GuessPacket(PacketType):
    """
    This packet is sent by the client as a guess to what the random
    number is.
    """
    DEFINITION_IDENTIFIER = "rng_guessing.GuessPacket"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("game_id", UINT16),
        ("guess", UINT16)
    ]

class CorrectnessPacket(PacketType):
    """
    This packet is sent by the server as a response to whether
    the previous guess was correct or not.
    """
    DEFINITION_IDENTIFIER = "rng_guessing.CorrectnessPacket"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("game_id", UINT16),
        ("correct", BOOL)
    ]

def basicUnitTest():
    from playground.network.packet import FIELD_NOT_SET

    rng_request1 = RequestRandomNumberPacket()
    rng_request1_bytes = rng_request1.__serialize__()
    rng_request1_deserialzed = RequestRandomNumberPacket.Deserialize(rng_request1_bytes)
    assert rng_request1 == rng_request1_deserialzed


    rng_problem1 = RandomNumberProblemPacket(min_range=0, max_range=10, game_id=0)
    rng_problem2 = RandomNumberProblemPacket(min_range=0, max_range=11)
    assert rng_problem1.min_range == 0
    assert rng_problem1.max_range == 10
    assert rng_problem1.game_id == 0
    assert rng_problem2.min_range == 0
    assert rng_problem2.max_range == 11
    assert rng_problem2.game_id == FIELD_NOT_SET

    rng_problem2.max_range = rng_problem1.max_range
    assert rng_problem2.max_range == rng_problem1.max_range

    rng_problem2.game_id = 1
    assert rng_problem2.game_id-1 == rng_problem1.game_id

    deserializer = RandomNumberProblemPacket.Deserializer()

    deserializer.update(rng_problem1.__serialize__())
    deserializer.update(rng_problem2.__serialize__())
    packets = list(deserializer.nextPackets())

    assert packets[0] == rng_problem1 and packets[1] == rng_problem2


    guess_packet1 = GuessPacket(guess=9)
    assert guess_packet1.game_id == FIELD_NOT_SET

    guess_packet1.game_id=3
    assert guess_packet1.guess == 9

    guess_packet2 = GuessPacket(guess=9, game_id=4)
    assert guess_packet1 != guess_packet2

    guess_packet1_des = PacketType.Deserialize(guess_packet1.__serialize__())
    assert guess_packet1_des == guess_packet1

    correctness_packet1 = CorrectnessPacket(game_id=2)
    assert correctness_packet1.correct == FIELD_NOT_SET

    correctness_packet1.correct = False
    assert correctness_packet1.correct == False

    correctness_packet2 = CorrectnessPacket(game_id=5, correct=True)
    assert correctness_packet2.correct == True

    serialized_data = correctness_packet2.__serialize__() + correctness_packet1.__serialize__() + correctness_packet2.__serialize__()
    packets = []
    deserializer = CorrectnessPacket.Deserializer()
    while serialized_data:
        chunk, serialized_data = serialized_data[:10], serialized_data[10:]
        deserializer.update(chunk)
        for p in deserializer.nextPackets():
            packets.append(p)

    assert packets[0] == correctness_packet2 and packets[1] == correctness_packet1 and packets[2] == correctness_packet2


if __name__ == "__main__":
    basicUnitTest()
    print("Basic unit test completed successfully.")
