import sys
import os
import logging

import grpc

# makes it possible to put generated grpc code in 
# seperate folder and still have the imports work
sys.path.append(os.path.join(os.getcwd(), "generated"))

from generated import chat_pb2, chat_pb2_grpc

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = chat_pb2_grpc.ChatStub(channel)
        empty = chat_pb2.Empty()
        response = stub.GetAccounts(empty)

    print("Client received: \n" + str(response))

if __name__ == '__main__':
    logging.basicConfig()
    run()