import os
import ssl
import socket
import sys

CERT_DIR = f"/certs/ml-dsa-{os.environ.get('ML_DSA_LEVEL', '44')}"
PORT = 8443


def main():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(certfile=f"{CERT_DIR}/server.pem", keyfile=f"{CERT_DIR}/server.key")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", PORT))
        sock.listen(5)
        print(f"TLS server (server-auth only) listening on :{PORT}", flush=True)
        while True:
            conn, addr = sock.accept()
            try:
                with ctx.wrap_socket(conn, server_side=True) as ssock:
                    print(f"handshake OK with {addr}: {ssock.version()} {ssock.cipher()}", flush=True)
                    try:
                        ssock.recv(4096)
                    except Exception:
                        pass
                    ssock.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            except (ssl.SSLError, OSError) as e:
                print(f"connection FAILED with {addr}: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
