# Classical (RSA/ECDSA) certs

Placeholder — this is the classical baseline for the ML-DSA-vs-classical
performance comparison in the project Goals. Cert generation here is
self-service (unlike the ML-DSA levels, there's no EJBCA/DigiCert-Labs
dependency — any RSA or ECDSA cert works, including a plain self-signed
one via `openssl req -x509`), so nothing is committed yet:

- `server.key` — private key. **Not committed** (gitignored), same policy
  as every other `*.key` in `certs/`.
- `server.pem` — self-signed leaf certificate. RSA-2048 or ECDSA
  P-256 are the natural choices — whichever gives the most useful
  apples-to-apples comparison against ML-DSA-44 (roughly comparable
  security level to RSA-2048/ECDSA P-256, per NIST's classical-equivalence
  guidance).
- `client.key` / `client.pem` — mTLS client identity (Phase 3), same
  shape as the ML-DSA levels' client material.

Once populated, the same `CN=pqc.poc.localhost`-style subject and
`certs/ml-dsa-44/`-style directory layout keeps the comparison tests
(`docs/test-cases.md`) able to treat this as just another cert level
alongside `ml-dsa-44/65/87`, differing only in which signature algorithm
it exercises.

These are lab/test certificates for local comparison benchmarking only —
not for production traffic.
