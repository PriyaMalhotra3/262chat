# Wire Protocol

The 262chat Part 1 Wire Protocol is a stateful, text-based, centralized messaging protocol between a client and a central server over a [TCP (Transmission Control Protocol)](https://www.ietf.org/rfc/rfc793.txt) port. All strings are encoded in [UTF-8](https://www.ietf.org/rfc/rfc3629.txt).

The protocol is stateful, and has two phases: the [**Association Phase**](#association-phase) and the [**Streaming Phase**](#streaming-phase). Read below for specific details.

## Definitions

Throughout this wire protocol specificaiton document, the key words “must”, “must not”, “required”, “shall”, “shall not”, “should”, “should not”, “recommended”, “may”, and “optional” have the meaning defined in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

The following boldface definitions apply for the rest of this wire protocol specification document.

 - **Line**: a **line** is a [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) string ending with either `\r\n` or `\n`, and not containing any `\r` nor `\n` characters before the end. It is matched by the [POSIX Regular Expression](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html) `[^\r\n]*\r?\n`. Servers compliant with this protocol may output either `\r\n`-terminated lines or `\n`-terminated lines, and compliant clients must treat both types the same way.
 - **Null-terminated string**: a **null-terminated string** is a [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) string ending with `\0` (the null byte `0x00`) and not containing any `\0` characters before the end. It is matched by the [POSIX Regular Expression](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html) `[^\0]*\0`.
 - **Whitespace**: **whitespace** is any non-empty sequence of the following characters, in any combination and with possible repeats: `\r` (carriage return character), `\n` (newline character), `\t` (tab), `\f` (form feed character), `\v` (vertical tab), ` ` (space). It is matched by the [POSIX Regular Expression](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html) `[\r\n\t\f\v  ]+`.
 
## Association Phase

When a client connects to a server, it is in the association state. The server maintains a one-to-one map of online users to live [TCP](https://www.ietf.org/rfc/rfc793.txt) connections. Since the server does not know _a priori_ which user a new [TCP](https://www.ietf.org/rfc/rfc793.txt) connection is associated with, all clients start out in the association state. The only way to move out of the association phase is by either closing/dropping the connection to move into the dead state, or successful authentication by sending one of the following two commands. The client must send one of the following two commands as the first bytes it sends after connecting; otherwise, an [error response](#error-response) will be sent.

### REGISTER command 
#### `REGISTER user\0password\0`

A register command is the string [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) string .
