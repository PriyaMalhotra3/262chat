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

When a client connects to a server, it is in the association state. The server maintains a one-to-one map of online users to live [TCP](https://www.ietf.org/rfc/rfc793.txt) connections. Since the server does not know _a priori_ which user a new [TCP](https://www.ietf.org/rfc/rfc793.txt) connection is associated with, all clients start out in the association state. The only way to move out of the association state is by either closing/dropping the connection to move into the dead state, or successful authentication by sending one of the following two commands to move to the streaming state. The client must send one of the following two commands as the first bytes it sends after connecting; otherwise, an [error response](#error-response) will be sent.

### REGISTER command 
#### `REGISTER user\0password\0`

A register command is a sequence of two **null-terminated string**s, which combined follow the above template. Compliant servers should be able to tolerate any kind of **whitespace** following the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `REGISTER`, not just a single space ` `. The command asks the server to register a new user with the username `user` and password `password`. `user` must not contain **whitespace** or be empty (in which case it would be an invalid username). `password\0` can be any **null-terminated string**. If and only `user` is not an invalid username and `user` is not already a username of another user on the server, a [success response](#success-response) is sent and the client enters the [streaming phase](#streaming-phase) as `user`. In all other cases, an [error response](#error-response) is returned, and the client stays in the association state.

### LOGIN command
#### `LOGIN user\0password\0`

A login command is a sequence of two **null-terminated string**s, which combined follow the above template. Compliant servers should be able to tolerate any kind of **whitespace** following the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `LOGIN`, not just a single space ` `. The command asks the server to login an existing user with the username `user` and password `password`. If and only `user` is not an invalid username and has already been registered as user with the same `password` using the [register command](#register-command), a [success response](#success-response) is sent and the client enters the [streaming phase](#streaming-phase) as `user`. In all other cases, an [error response](#error-response) is returned, and the client stays in the association state.

### ERROR response
#### `ERROR message\0`

An error response from the server is a single **null-terminated string** which follows the above template. Compliant clients should be able to tolerate any kind of **whitespace** following the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `ERROR`, not just a single space ` `. `message` is a [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) string that provides a user-friendly description of why the client failed authentication. When a client receives this response, the only commands it can send are still just retrying the [register command](#register-command) or the [login command](#login-command), because it is still in the association state. If it tries to send any other bytes, it will receive another [error response](#error-response) after the first null byte `\0` and continue to stay in the association state.

### SUCCESS response
#### `SUCCESS You are logged in.\0`

An success response from the server is the above **null-terminated string**. Clients that receive a success response have entered the [streaming phase](#streaming-phase), which means, among other things, that they may being receiving messages unprompted from other users directed at them and that they can use (only) the commands listed in the [streaming phase](#streaming-phase) of this wire protocol specification document.

## Streaming Phase

### MESSAGE response
#### `MESSAGE sender\nSent: 1984-02-07T12:34:56789+09:00\nbody\0`

A message response from the server is a single **null-terminated string** which follows the above template, representing an inbound message from `sender`. Compliant clients should be able to tolerate any kind of **whitespace** following the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `MESSAGE` and `Sent:`, not just a single space ` `, and recognize `\r\n` as an alternative for `\n`. When clients are in the streaming state, the server can send them message responses in the interim between any other complete responses. However, compliant servers must ensure that message responses do not interrupt other responses before they are complete ([`part1/server.py`](server.py#L90-L94) ensure this by [holding a per-session lock](server.py#L90-L94) during any send operation to a client). After `Sent:` and **whitespace**, compliant servers should send a [ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) format date-and-time string representing the date-and-time that the server received the message from the `sender`. `body` contains the body of the message.

### MESSAGE command
#### `MESSAGE recipient\nbody\0`

A message command is a single **null-terminated string** which follows the above template, representing an outbound message to `recipient`. Compliant clients should be able to tolerate any kind of **whitespace** following the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `MESSAGE`, not just a single space ` `, and recognize `\r\n` as an alternative for `\n`. A properly formatted message that is received in full by the server will generate a [sent response](#sent-response), while any formatting issues or non-existence of the `recipient` will generate an [streaming phase](#streaming-phase) specific error response (see below).

### SENT response
#### `SENT\0`

An sent response from the server is the above **null-terminated string**, which represents that the message in the last-processed [message command](#message-command) has been successfully received in full by the server and is en route to its recipient (either queued, waiting for the recipient to come back online, or immediately delivered).

### LIST command
#### `LIST [patt*rn]\0`

A list command is a single **null-terminated string** which follows the above template. Compliant servers should be able to tolerate any kind of **whitespace** following the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `LIST`, not just a single space ` `. `[patt*rn]` is an optional Unix shell-style wildcard to filter the returned user list by, as defined by [Python `fnmatch`](https://docs.python.org/3/library/fnmatch.html). If `[patt*rn]` is not provided, `*` is assumed. When `[patt*rn]` is not provided, **whitespace** need not follow the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `LIST`. The list of users, optionally filtered by `[patt*rn]` will be returned in a [listing response](#listing-response).

### LISTING response
#### `LISTING\nusername1\nusername2[ (online)]\n...\0`

A listing response is a single **null-terminated string** containing multiple **line**s that follow the above template. Compliant clients should be able to recognize `\r\n` as an alternative for `\n`. The first line will just be the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `LISTING`, and every following line contains the username of a user that matched the `[patt*rn]` from the [list command](#list-command) which generated the listing response. Servers may choose to append **whitespace** and the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `(online)` after any username in the listing if the server supports user-presence-tracking. Compliant clients should be able to gracefully handle both lack and existence of user-presence data, and be able to tolerate any kind of **whitespace** preceding the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `(online)`, not just a single space ` `.

### DELETE command
#### `DELETE\0`

A delete command from the client is the above **null-terminated string**, which requests that the server delete the user associated with the current session and all their data from the server and disconnect the user. This command always succeeds and generates a [deleted response](#deleted-response) upon receipt by the server, followed by the server closing the connection with the client.

### DELETED response
#### `DELETED Account deleted; you are being disconnected.\0`

An sent response from the server is the above **null-terminated string**, which represents that the user associated with the current session is being deleted and that the current session is being closed by the sever. No more responses can come from the server after this response.

### ERROR response
#### `ERROR message\0`

An error response from the server during the [streaming phase](#streaming-phase) is a single **null-terminated string** which follows the above template. Compliant clients should be able to tolerate any kind of **whitespace** following the [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) bytes for `ERROR`, not just a single space ` `. `message` is a [UTF-8](https://www.ietf.org/rfc/rfc3629.txt) string that provides a user-friendly description of why a [streaming phase](#streaming-phase) command was incorrectly formatted. The only three sources of this response in the [streaming phase](#streaming-phase) are

 1. sending bytes other [streaming phase](#streaming-phase) commands
 1. incorrect formatting of the last-processed [message command](#message-command)
 1. the `recipient` of the last-processed [message command](#message-command) is not a user on this server
