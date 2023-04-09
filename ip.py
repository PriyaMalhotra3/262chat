import socket
import re
from ipaddress import ip_address

ADDRESS_REGEX = re.compile(r"^(?:(?:ipv4:)?(?P<ipv4>[\d.]+)|(?:ipv6:)?\[(?P<ipv6>[a-fA-F\d:]+)\]):(?P<port>\d+)$")

def parse_address(ip_and_port: str):
    m = ADDRESS_REGEX.match(ip_and_port)
    if not m:
        raise ValueError(f"'{s}' is not in the format 'ipv4:port' or '[ipv6]:port'")
    str(ip_address(m["ipv4"] or m["ipv6"])), int(m["port"])

def local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # UDP does not actually send packets on `connect`, this is just to get the local IP address.
        sock.connect(("8.8.8.8", 80)) # Public DNS.
        return sock.getsockname()[0]
