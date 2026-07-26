import os
import socket
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_DSA_LEVEL = "44"
CERT_DIR = REPO_ROOT / "certs" / f"ml-dsa-{ML_DSA_LEVEL}"
CERT_FILE = CERT_DIR / "server.pem"
KEY_FILE = CERT_DIR / "server.key"

# Matches the host ports docker-compose.yml maps each language's service to.
# All three serve the same certs/ml-dsa-44 material.
SERVICE_PORTS = {
    "python": 443,
    "java": 8444,
    "javascript": 8544,
}


def pytest_addoption(parser):
    parser.addoption(
        "--server-host",
        default=os.environ.get("PQC_TEST_HOST", "localhost"),
        help="host the TLS servers are listening on",
    )
    parser.addoption(
        "--language",
        choices=sorted(SERVICE_PORTS),
        default=None,
        help="restrict live tests to a single language's service (default: all three)",
    )


@pytest.fixture(scope="session", params=sorted(SERVICE_PORTS))
def language(request):
    only = request.config.getoption("--language")
    if only and request.param != only:
        pytest.skip(f"--language={only} excludes {request.param}")
    return request.param


@pytest.fixture(scope="session")
def server_address(request, language):
    return request.config.getoption("--server-host"), SERVICE_PORTS[language]


@pytest.fixture
def cert_file():
    if not CERT_FILE.exists():
        pytest.skip(f"{CERT_FILE} not found")
    return CERT_FILE


@pytest.fixture
def key_file():
    if not KEY_FILE.exists():
        pytest.skip(f"{KEY_FILE} not found (gitignored — see certs/ml-dsa-44/README.md)")
    return KEY_FILE


@pytest.fixture(scope="session")
def _server_reachable(server_address):
    host, port = server_address
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture
def require_live_server(_server_reachable, server_address, language):
    if not _server_reachable:
        host, port = server_address
        pytest.skip(
            f"no {language} server reachable at {host}:{port} — start it with "
            "`docker compose up --build`, then run tests via scripts/run_tests.sh "
            "(host OpenSSL/curl typically can't speak ML-DSA TLS at all)"
        )
