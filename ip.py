import socket

def local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # UDP does not actually send packets on `connect`, this is just to get the local IP address.
        sock.connect(("8.8.8.8", 80)) # Public DNS.
        return sock.getsockname()[0]
