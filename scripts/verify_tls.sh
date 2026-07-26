#!/usr/bin/env bash
# Checks an ML-DSA TLS endpoint from inside a python:3.13-slim-trixie
# container (OpenSSL 3.5+), since most host toolchains - system openssl -
# and every mainstream desktop browser as of today - don't yet support
# ML-DSA TLS handshakes at all. A connection failure from your host doesn't
# necessarily mean the server is broken; use this first.
#
# Completes the handshake and sends a test message, expecting the server's
# raw-TLS echo response back (see servers/*/README.md) - no HTTP involved.
#
# Usage: scripts/verify_tls.sh <port> [host]
set -euo pipefail

PORT="${1:?usage: verify_tls.sh <port> [host]}"
HOST="${2:-localhost}"

docker run --rm --network host python:3.13-slim-trixie python3 -c "
import socket, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
with socket.create_connection(('${HOST}', ${PORT}), timeout=5) as sock:
    with ctx.wrap_socket(sock, server_hostname='${HOST}') as tls:
        print(f'TLS version: {tls.version()}, cipher: {tls.cipher()}')
        tls.sendall(b'verify_tls.sh check')
        print('Server replied:', tls.recv(4096))
"
