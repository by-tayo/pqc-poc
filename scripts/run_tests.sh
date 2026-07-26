#!/usr/bin/env bash
# Runs the pytest suite (scripts/tests/) inside a python:3.13-slim-trixie
# container (OpenSSL 3.5+), for the same reason scripts/verify_tls.sh does:
# ML-DSA TLS handshakes need it, and most host toolchains don't have it yet.
# Cert-material tests still run fine on the host and self-skip the
# ML-DSA-specific/live-server bits with a clear reason if unsupported, but
# this is the one command that gets full coverage.
#
# Builds a throwaway image (COPY, not a bind mount — bind-mounting a
# \\wsl.localhost UNC path doesn't resolve correctly through Docker
# Desktop on Windows) so it works the same way `docker compose build` does.
#
# Assumes the server is already up: docker compose up --build
# Usage: scripts/run_tests.sh [pytest args...]
set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE="pqc-poc-tests"

docker build -t "$IMAGE" -f - . <<'DOCKERFILE'
FROM python:3.13-slim-trixie
WORKDIR /workspace
COPY pytest.ini /workspace/pytest.ini
COPY scripts/tests /workspace/scripts/tests
COPY certs /workspace/certs
RUN pip install --quiet --disable-pip-version-check -r scripts/tests/requirements.txt
DOCKERFILE

CONTAINER="pqc-poc-tests-run-$$"
STATUS=0
docker run --name "$CONTAINER" --network host "$IMAGE" python -m pytest scripts/tests -v "$@" || STATUS=$?

mkdir -p results/metrics
docker cp "$CONTAINER:/workspace/results/metrics/." results/metrics/ 2>/dev/null || true
docker rm "$CONTAINER" >/dev/null

exit "$STATUS"
