# Test case matrix

Dimensions: endpoint (Python / Java / JS / **Apache**) × cert (ML-DSA-44 /
ML-DSA-65 / ML-DSA-87 / **classical-rsa**) × **auth mode (TLS / mTLS)** ×
**key exchange (classical / hybrid ECDHE+ML-KEM)** × **network path
(local / single-region GCP / cross-region GCP)** × scenario. Apache,
mTLS, the classical-cert baseline, hybrid key exchange, and the
cross-region network path are all new as of the EJBCA/GCP expansion —
see the repo root `README.md` Roadmap section.

## Scenarios

| Scenario     | What it checks                                                  |
|--------------|-------------------------------------------------------------------|
| Compatibility| Handshake succeeds across client/server/browser combinations      |
| Performance  | Handshake timing, cert/key sizes, bytes on wire, CPU cost — ML-DSA vs. classical-rsa is the headline comparison here; repeated across network paths to see whether the gap changes with real-world latency |
| Validation   | Chain validation, trust store acceptance/rejection                |
| **mTLS auth**| Client cert required and validated; connection rejected without one, or with an untrusted one |
| **Hybrid KEM**| TLS 1.3 negotiates a hybrid group (e.g. `X25519MLKEM768`) instead of a classical-only group, independent of which cert/signature algorithm is in use |
| Issue        | Cert issuance flow via EJBCA (see `infra/ejbca/README.md`) for ML-DSA; self-service `openssl req` for classical-rsa |
| Renew        | Renewal flow, continuity of trust                                 |
| Revoke       | CRL revocation is honored by clients (OCSP for ML-DSA is still in development upstream — see `infra/ejbca/README.md`'s "Known limitation") |

Cert source note: ML-DSA-44's currently-committed `server.pem` is still
DigiCert PQC Labs-issued; everything else (client certs at every level,
and server certs once Phase 3 lands) comes from the local EJBCA CA;
`classical-rsa/` is self-generated, no CA dependency. See
`certs/ml-dsa-44/README.md` and `certs/classical-rsa/README.md` for the
exact per-level state.

## Status

Not yet run systematically. Fill in a row per (endpoint, cert, auth mode,
scenario) combination as tests are executed, linking to the relevant file
under `results/performance/`. The TLS-only, ML-DSA-44-only rows already
covered by `scripts/tests/` are described in "Findings so far" below;
mTLS and the other two cert levels are still open — that's what `tests/`
(see `tests/README.md`) is for.

## Findings so far

All three languages are now verified working for **ML-DSA-44 only**
(ML-DSA-65/87 are still placeholders - not yet re-tested at those levels).
`scripts/tests/` (run via `scripts/run_tests.sh`) exercises all three
automatically; 28/28 passing as of the last full run (against
`servers/`'s bare TLS servers — no HTTP layer, see the root README).

- **Python**: works end-to-end, no extra libraries - stdlib `ssl` + OpenSSL
  3.5+ via `python:3.13-slim-trixie`. TLS 1.3 handshake confirmed.
- **JavaScript**: works end-to-end, no extra libraries either - Node 22/24's
  built-in `tls` module loads and serves the cert directly, since
  Node already bundles OpenSSL 3.5.7. Genuinely the easiest of the three.
- **Java**: stock JDK 25 (current LTS) **cannot** terminate an ML-DSA TLS
  connection - JCA algorithm support exists, but JSSE's certificate-selection
  logic doesn't recognize ML-DSA as an authentication scheme at all
  (`SSLHandshakeException: No available authentication scheme`). **Fixed**
  with JDK 21 + BouncyCastle 1.85 (`bcprov`/`bcpkix`/`bctls-jdk18on`) via the
  BCJSSE provider - but BCJSSE also doesn't offer ML-DSA's still-draft TLS
  signature-scheme codepoints by default; needs
  `jdk.tls.{client,server}.SignatureSchemes` set explicitly to include
  `mldsa44`. See `servers/java/README.md` for the full writeup.
- **Browsers**: likely can't do an ML-DSA handshake either (same class of gap
  as stock JDK - a hard connection error, not just a self-signed-cert
  warning, is expected). Not yet confirmed against a specific browser/version.
