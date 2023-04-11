# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: chat.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import timestamp_pb2 as google_dot_protobuf_dot_timestamp__pb2
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\nchat.proto\x1a\x1fgoogle/protobuf/timestamp.proto\x1a\x1bgoogle/protobuf/empty.proto\")\n\x07Message\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x0c\n\x04text\x18\x02 \x01(\t\"4\n\x0e\x41uthentication\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x10\n\x08password\x18\x02 \x01(\t\"?\n\x0eInitialRequest\x12\x0e\n\x06\x63reate\x18\x01 \x01(\x08\x12\x1d\n\x04user\x18\x02 \x01(\x0b\x32\x0f.Authentication\"G\n\x0bSentMessage\x12\x19\n\x07message\x18\x01 \x01(\x0b\x32\x08.Message\x12\x1d\n\x04user\x18\x02 \x01(\x0b\x32\x0f.Authentication\"\x16\n\x06\x46ilter\x12\x0c\n\x04glob\x18\x01 \x01(\t\"\x1a\n\x05Users\x12\x11\n\tusernames\x18\x01 \x03(\t\"V\n\x0fReceivedMessage\x12\x19\n\x07message\x18\x01 \x01(\x0b\x32\x08.Message\x12(\n\x04sent\x18\x02 \x01(\x0b\x32\x1a.google.protobuf.Timestamp2\xcc\x01\n\x04\x43hat\x12\x31\n\x08Initiate\x12\x0f.InitialRequest\x1a\x10.ReceivedMessage\"\x00\x30\x01\x12\x35\n\x0bSendMessage\x12\x0c.SentMessage\x1a\x16.google.protobuf.Empty\"\x00\x12:\n\rDeleteAccount\x12\x0f.Authentication\x1a\x16.google.protobuf.Empty\"\x00\x12\x1e\n\tListUsers\x12\x07.Filter\x1a\x06.Users\"\x00\x62\x06proto3')



_MESSAGE = DESCRIPTOR.message_types_by_name['Message']
_AUTHENTICATION = DESCRIPTOR.message_types_by_name['Authentication']
_INITIALREQUEST = DESCRIPTOR.message_types_by_name['InitialRequest']
_SENTMESSAGE = DESCRIPTOR.message_types_by_name['SentMessage']
_FILTER = DESCRIPTOR.message_types_by_name['Filter']
_USERS = DESCRIPTOR.message_types_by_name['Users']
_RECEIVEDMESSAGE = DESCRIPTOR.message_types_by_name['ReceivedMessage']
Message = _reflection.GeneratedProtocolMessageType('Message', (_message.Message,), {
  'DESCRIPTOR' : _MESSAGE,
  '__module__' : 'chat_pb2'
  # @@protoc_insertion_point(class_scope:Message)
  })
_sym_db.RegisterMessage(Message)

Authentication = _reflection.GeneratedProtocolMessageType('Authentication', (_message.Message,), {
  'DESCRIPTOR' : _AUTHENTICATION,
  '__module__' : 'chat_pb2'
  # @@protoc_insertion_point(class_scope:Authentication)
  })
_sym_db.RegisterMessage(Authentication)

InitialRequest = _reflection.GeneratedProtocolMessageType('InitialRequest', (_message.Message,), {
  'DESCRIPTOR' : _INITIALREQUEST,
  '__module__' : 'chat_pb2'
  # @@protoc_insertion_point(class_scope:InitialRequest)
  })
_sym_db.RegisterMessage(InitialRequest)

SentMessage = _reflection.GeneratedProtocolMessageType('SentMessage', (_message.Message,), {
  'DESCRIPTOR' : _SENTMESSAGE,
  '__module__' : 'chat_pb2'
  # @@protoc_insertion_point(class_scope:SentMessage)
  })
_sym_db.RegisterMessage(SentMessage)

Filter = _reflection.GeneratedProtocolMessageType('Filter', (_message.Message,), {
  'DESCRIPTOR' : _FILTER,
  '__module__' : 'chat_pb2'
  # @@protoc_insertion_point(class_scope:Filter)
  })
_sym_db.RegisterMessage(Filter)

Users = _reflection.GeneratedProtocolMessageType('Users', (_message.Message,), {
  'DESCRIPTOR' : _USERS,
  '__module__' : 'chat_pb2'
  # @@protoc_insertion_point(class_scope:Users)
  })
_sym_db.RegisterMessage(Users)

ReceivedMessage = _reflection.GeneratedProtocolMessageType('ReceivedMessage', (_message.Message,), {
  'DESCRIPTOR' : _RECEIVEDMESSAGE,
  '__module__' : 'chat_pb2'
  # @@protoc_insertion_point(class_scope:ReceivedMessage)
  })
_sym_db.RegisterMessage(ReceivedMessage)

_CHAT = DESCRIPTOR.services_by_name['Chat']
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _MESSAGE._serialized_start=76
  _MESSAGE._serialized_end=117
  _AUTHENTICATION._serialized_start=119
  _AUTHENTICATION._serialized_end=171
  _INITIALREQUEST._serialized_start=173
  _INITIALREQUEST._serialized_end=236
  _SENTMESSAGE._serialized_start=238
  _SENTMESSAGE._serialized_end=309
  _FILTER._serialized_start=311
  _FILTER._serialized_end=333
  _USERS._serialized_start=335
  _USERS._serialized_end=361
  _RECEIVEDMESSAGE._serialized_start=363
  _RECEIVEDMESSAGE._serialized_end=449
  _CHAT._serialized_start=452
  _CHAT._serialized_end=656
# @@protoc_insertion_point(module_scope)
