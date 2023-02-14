import sys
import os
import logging
from concurrent import futures

import grpc

# makes it possible to put generated grpc code in 
# seperate folder and still have the imports work
sys.path.append(os.path.join(os.getcwd(), "generated"))

from generated import chat_pb2, chat_pb2_grpc

class Chat(chat_pb2_grpc.ChatServicer):
    def GetAccounts(self, request, context):
        accounts = chat_pb2.Accounts()
        accounts.accounts.append("acc_1")
        accounts.accounts.append("acc_2")

        return chat_pb2.Accounts(accounts=accounts.accounts)

    def GetMessages(self, request, context):
        messages = chat_pb2.Messages()
        message.append(chat_pb2.Message(
            sender="acc_1",
            receiver="acc_2",
            message="Hello, how are you?"
        ))
        message.append(chat_pb2.Message(
            sender="acc_2",
            receiver="acc_1",
            message="I'm fine, thank you!"
        ))
        
        return chat_pb2.Messages(messages)

def serve():
    port = '50051'

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServicer_to_server(Chat(), server)
    server.add_insecure_port('[::]:' + port)
    server.start()

    print("Server started, listening on " + port)
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig()
    serve()