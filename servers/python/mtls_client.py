import os
import ssl
import socket
import time

CERT_DIR = f"/certs/ml-dsa-{os.environ.get('ML_DSA_LEVEL', '44')}"
HOST = os.environ.get("HOST", "localhost")
PORT = 8444


def main():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cafile=f"{CERT_DIR}/ca-chain.pem")
    ctx.load_cert_chain(certfile=f"{CERT_DIR}/client.pem", keyfile=f"{CERT_DIR}/client.key")
    # server.pem has no subjectAltName (EJBCA's SERVER profile doesn't carry
    # the requested dNSName through) - CN only
    ctx.check_hostname = False

    with socket.create_connection((HOST, PORT)) as sock:
        t0 = time.perf_counter()
        with ctx.wrap_socket(sock, server_hostname="pqc.poc.localhost") as ssock:
            t1 = time.perf_counter()
            print(f"handshake OK: {ssock.version()} {ssock.cipher()}")
            print(f"handshake time: {(t1 - t0) * 1000:.2f} ms")
            ssock.sendall(b"GET / HTTP/1.1\r\nHost: pqc.poc.localhost\r\n\r\n")
            print(ssock.recv(4096).decode(errors="replace"))


if __name__ == "__main__":
    main()
