# ML-DSA-44 certs

All four files are issued by the same source: the local EJBCA CA
`ML-DSA-44-CA` (see `infra/ejbca/README.md`), an ML-DSA-44 root created via
`ca init` in EJBCA Community Edition - no Enterprise license needed.

- `server.pem` / `server.key` — server identity, `CN=pqc.poc.localhost`.
  No `subjectAltName` - EJBCA's `SERVER` certificate profile didn't carry
  the requested `dNSName` through even with `--altname` set on the end
  entity (would need profile-level SAN-type configuration to fix; not
  pursued). Clients work around this with CN-only checks - see each
  `servers/<lang>/README.md`.
- `client.pem` / `client.key` — mTLS client identity, `CN=pqc-poc-client-44`.
- `ca-chain.pem` — the CA's own certificate. Both sides trust this: servers
  validate presented client certs against it, clients validate the server
  cert against it too, since `server.pem` now chains to the same CA.

`*.key` files are gitignored - private keys stay local only, even for
lab/trial material, since this repo is public.

Still lab/trial-only, not for production traffic. Regenerate by reproducing
the EJBCA CLI flow in `infra/ejbca/README.md` (crypto token → CA → CSR →
issued cert) if this material is ever lost or needs rotating.
