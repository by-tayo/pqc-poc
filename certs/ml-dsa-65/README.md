# ML-DSA-65 certs

All four files are issued by the same source: the local EJBCA CA
`ML-DSA-65-CA` (see `infra/ejbca/README.md`), an ML-DSA-65 root created via
`ca init` in EJBCA Community Edition - no Enterprise license needed.

- `server.pem` / `server.key` — server identity, `CN=pqc.poc.localhost`.
  No `subjectAltName` - same EJBCA `SERVER` certificate profile limitation
  as ML-DSA-44 (see `certs/ml-dsa-44/README.md`).
- `client.pem` / `client.key` — mTLS client identity, `CN=pqc-poc-client-65`.
- `ca-chain.pem` — the CA's own certificate, trusted by both sides.

`*.key` files are gitignored - private keys stay local only, even for
lab/trial material, since this repo is public.

Still lab/trial-only, not for production traffic. Regenerate by reproducing
the EJBCA CLI flow in `infra/ejbca/README.md` if this material is ever lost
or needs rotating.
