"""Static checks against certs/ml-dsa-44/server.{pem,key} — no server needed.

Uses ssl._ssl._test_decode_cert() (the private helper backing
SSLSocket.getpeercert()) to read subject/issuer/validity fields, since that
only walks the TBSCertificate ASN.1 structure and works on any OpenSSL,
unlike loading the key material itself which needs ML-DSA support
(OpenSSL 3.5+, see scripts/verify_tls.sh).
"""

import base64
import ssl
from datetime import datetime, timezone

import pytest

# DER encoding of OID 2.16.840.1.101.3.4.3.17 (id-ml-dsa-44): tag 0x06,
# length 0x09, then the base-128 encoded arcs.
ML_DSA_44_SIGNATURE_OID_DER = bytes.fromhex("0609608648016503040311")


def _der_bytes(pem_path):
    text = pem_path.read_text()
    body = "".join(line for line in text.splitlines() if line and "-----" not in line)
    return base64.b64decode(body)


def _parse_x509_time(value):
    # X.509 time strings are always GMT, e.g. "Jul 15 01:20:23 2026 GMT".
    naive = datetime.strptime(value[:-4], "%b %d %H:%M:%S %Y")
    return naive.replace(tzinfo=timezone.utc)


def test_pem_file_is_nonempty(cert_file):
    assert cert_file.stat().st_size > 0


def test_pem_is_decodable(cert_file):
    info = ssl._ssl._test_decode_cert(str(cert_file))
    assert info["version"] == 3


def test_subject_common_name(cert_file):
    info = ssl._ssl._test_decode_cert(str(cert_file))
    subject = dict(entry[0] for entry in info["subject"])
    assert subject["commonName"] == "pqc.poc.localhost"


def test_certificate_is_self_signed(cert_file):
    info = ssl._ssl._test_decode_cert(str(cert_file))
    assert info["subject"] == info["issuer"]


def test_certificate_currently_valid(cert_file):
    info = ssl._ssl._test_decode_cert(str(cert_file))
    not_before = _parse_x509_time(info["notBefore"])
    not_after = _parse_x509_time(info["notAfter"])
    now = datetime.now(timezone.utc)
    assert not_before <= now <= not_after


def test_signature_algorithm_is_ml_dsa_44(cert_file):
    der = _der_bytes(cert_file)
    assert ML_DSA_44_SIGNATURE_OID_DER in der


def test_private_key_loads_with_certificate(cert_file, key_file):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    except ssl.SSLError as exc:
        pytest.skip(
            f"host OpenSSL ({ssl.OPENSSL_VERSION}) can't load an ML-DSA key/cert "
            f"({exc}); run via scripts/run_tests.sh for an OpenSSL 3.5+ environment"
        )
