# 262chat

## Testing

```shell
$ python3 -m test
```

## Installation

```shell
pip3 install -r requirements.txt
```

## Generate protobuf

```
cd part2

python3 -m grpc_tools.protoc -I . --python_out=./generated --pyi_out=./generated --grpc_python_out=./generated chat.proto
```

## Run server

```
cd part2
python3 server.py
```

## Run client

```
cd part2
python3 client.py
```
