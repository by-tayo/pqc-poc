# pqc-poc

A post-quantum TLS test bed covering both authentication and key
exchange, benchmarked against classical cryptography across multiple
language runtimes and deployment targets.

## Overview

This project evaluates two independent problems in migrating TLS to
post-quantum cryptography:

- **Authentication** — PQC digital-signature certificates (ML-DSA-44,
  ML-DSA-65, ML-DSA-87) benchmarked against classical RSA/ECDSA
  certificates, issued by a self-hosted EJBCA certificate authority.
- **Key exchange** — hybrid TLS 1.3 groups combining classical ECDHE
  with an ML-KEM (Kyber) key encapsulation mechanism, the standard
  approach for post-quantum-ready key establishment.

The current implementation runs bare TLS servers in Python, Java, and
JavaScript — no HTTP layer, driven from the command line and by
automated scripts rather than a browser — containerized with Docker and
tested locally. The roadmap extends this to mutual TLS (mTLS), a
classical certificate baseline, hybrid key exchange, and deployment on
Google Cloud Platform: Compute Engine VMs running the same Docker
Compose stack (EJBCA, Apache, and the three TLS servers) used locally,
including a pair of VMs in geographically distant regions to measure
handshake performance across real network latency instead of a single
machine's loopback. No Kubernetes — plain Docker on GCP VMs is all this
project's testing goals need.

Verification tooling spans OpenSSL, native-language TLS clients, and
Wireshark packet captures. Performance — handshake timing, certificate
and key size, CPU and bandwidth cost, and how that cost changes with
real network distance between client and server — is the primary
benchmark, alongside compatibility, certificate chain validation, and
certificate lifecycle (issuance, renewal, revocation).

## Features

| Area | Status |
|---|---|
| ML-DSA-44/65/87 TLS (Python, Java, JavaScript) | Implemented |
| EJBCA-issued certificates | Implemented — all server/client certs issued by a local EJBCA CA per level, see `infra/ejbca/README.md` |
| Mutual TLS (mTLS) | Implemented — see each `servers/<lang>/README.md` |
| Classical certificate baseline (RSA/ECDSA) | Planned |
| Hybrid key exchange (ECDHE + ML-KEM) | Planned |
| GCP deployment (Compute Engine VMs, Docker Compose) | Planned |
| Cross-region latency benchmarking (two VMs, different countries) | Planned |
| Multi-tool test harness (OpenSSL, Python, Node.js, Java, Wireshark) | In progress — see `tests/` |

## Project Structure

```
certs/                  Certificate material per algorithm (server, client, CA chain)
  ml-dsa-44/
  ml-dsa-65/
  ml-dsa-87/
  classical-rsa/         Classical baseline for comparison benchmarks
servers/                 Bare TLS servers (no HTTP layer), one per language
  python/
  java/
  js/
infra/
  ejbca/                 EJBCA (certificate authority) setup and configuration
captures/wireshark/      Packet captures of TLS handshakes
results/
  performance/           Test reports per run
  metrics/               Raw and tabulated metric data
scripts/
  benchmark/             Handshake benchmarking scripts
  capture/               tshark/dumpcap automation
  tests/                 Automated pytest regression suite (TLS-only)
tests/                   Multi-tool TLS/mTLS verification (OpenSSL, Python, Node.js, Java, Wireshark)
docs/
  test-cases.md          Test case matrix
```

## Getting Started

```bash
docker compose up --build
```

Starts the Python, Java, and JavaScript servers on ports 443, 8444, and
8544 respectively, each serving an ML-DSA-44 certificate over TLS 1.3.

Run the automated test suite:

```bash
scripts/run_tests.sh
```

## Certificate Sources

ML-DSA certificates for all three levels are issued by a self-hosted
EJBCA certificate authority (`infra/ejbca/README.md`) — one root CA per
level (`ML-DSA-44-CA`, `ML-DSA-65-CA`, `ML-DSA-87-CA`), each signing that
level's own server and client certs. Private keys are never committed —
see `.gitignore` and each certificate directory's README for details.

## Status

ML-DSA-44/65/87 are implemented end-to-end across all three languages,
covering both server-authenticated TLS and mutual TLS, verified against
`openssl s_client` and `curl` in addition to each language's own client.
The Java implementation requires JDK 21 with BouncyCastle, since standard
JSSE does not support ML-DSA certificate authentication (see
`servers/java/README.md`). Tested locally only — GCP deployment (Phase 5)
hasn't started.

## Roadmap

0. **EJBCA validation** *(complete)* — Confirmed EJBCA Community Edition
   issues valid ML-DSA-44/65/87 certificates without an Enterprise
   license. See `infra/ejbca/README.md`.
1. **Repository restructuring** *(complete)* — Added client certificate
   and CA chain slots per algorithm; introduced the multi-tool test
   harness structure.
2. **Classical baseline and hybrid key exchange** — RSA/ECDSA
   certificates for comparison benchmarking, and TLS 1.3 hybrid key
   exchange groups (e.g. `X25519MLKEM768`), supported natively by
   OpenSSL 3.5+ and Node.js 22+. Independent of the mTLS and GCP work
   below.
3. **Local mTLS** — Apache as a reverse proxy and mTLS gateway in front
   of the application servers, using EJBCA-issued client certificates.
4. **Test harness implementation** — OpenSSL, Python, Node.js, Java, and
   Wireshark test cases against the local mTLS stack.
5. **GCP deployment** — A Compute Engine VM running the full Docker
   Compose stack (EJBCA, Apache, and the three TLS servers) — the same
   stack from Phase 3, moved to a real network instead of localhost. No
   Kubernetes; the testing goals here don't need orchestration, just a
   real cloud VM to test TLS/mTLS against.
6. **Cross-region latency benchmarking** — A second VM in a
   geographically distant GCP region (e.g. a different continent from
   Phase 5's VM), running the test-client harness against it — a real
   client/server pair in different countries, not same-machine loopback.
   Compares handshake timing at low latency (single region) against high
   latency (cross-region), since ML-DSA's larger certificates/keys put
   more bytes on the wire than RSA/ECDSA and it's worth knowing whether
   that shows up more as round-trip time grows.
7. **Cloud validation** — Test harness extended to target both the
   single-region and cross-region GCP deployments.
