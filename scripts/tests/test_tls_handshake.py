"""Live handshake behavior against the running python-tls-44 server.

Requires an OpenSSL 3.5+ client (see scripts/verify_tls.sh) — run via
scripts/run_tests.sh for full coverage. All tests here skip cleanly if no
server is reachable at --server-host/--server-port (default localhost:443).
"""

import socket
import ssl

import pytest


def _connect(server_address, server_hostname):
    host, port = server_address
    return socket.create_connection((host, port), timeout=5), server_hostname or host


def _permissive_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _trusting_context(cert_file, check_hostname):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = check_hostname
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cafile=str(cert_file))
    return ctx


def test_handshake_succeeds_without_verification(require_live_server, server_address):
    sock, hostname = _connect(server_address, None)
    with _permissive_context().wrap_socket(sock, server_hostname=hostname) as tls:
        assert tls.version() is not None


def test_handshake_negotiates_tls13(require_live_server, server_address):
    sock, hostname = _connect(server_address, None)
    with _permissive_context().wrap_socket(sock, server_hostname=hostname) as tls:
        assert tls.version() == "TLSv1.3"


def test_verification_succeeds_when_cert_is_trusted(require_live_server, server_address, cert_file):
    sock, hostname = _connect(server_address, None)
    ctx = _trusting_context(cert_file, check_hostname=False)
    with ctx.wrap_socket(sock, server_hostname=hostname) as tls:
        peer = tls.getpeercert()
    subject = dict(entry[0] for entry in peer["subject"])
    assert subject["commonName"] == "pqc.poc.localhost"


def test_hostname_matches_via_cn_fallback(require_live_server, server_address, cert_file):
    # The cert carries no Subject Alternative Name extension, so OpenSSL
    # falls back to matching SNI against the Subject CN (pqc.poc.localhost).
    sock, _ = _connect(server_address, None)
    ctx = _trusting_context(cert_file, check_hostname=True)
    with ctx.wrap_socket(sock, server_hostname="pqc.poc.localhost") as tls:
        assert tls.version() == "TLSv1.3"


def test_hostname_mismatch_is_rejected(require_live_server, server_address, cert_file):
    sock, _ = _connect(server_address, None)
    ctx = _trusting_context(cert_file, check_hostname=True)
    try:
        with pytest.raises(ssl.SSLCertVerificationError):
            ctx.wrap_socket(sock, server_hostname="wrong-host.example")
    finally:
        sock.close()


def test_verification_fails_against_system_trust_store(require_live_server, server_address):
    # What a real browser/OS sees: a self-signed cert in nobody's trust
    # store, so default verification must fail — see the root README's
    # status notes on browser/host tooling support.
    sock, hostname = _connect(server_address, None)
    try:
        with pytest.raises(ssl.SSLCertVerificationError):
            ssl.create_default_context().wrap_socket(sock, server_hostname=hostname)
    finally:
        sock.close()
