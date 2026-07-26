# tests/openssl/

Not yet written — Phase 3.

Will use `openssl s_client -connect <host>:<port> [-cert client.pem -key
client.key] -CAfile ca-chain.pem` to drive both plain-TLS and mTLS
handshakes against each endpoint (python/java/js/apache) at each available
cert level, asserting success/failure via exit code and by parsing the
peer certificate `openssl s_client` prints on stderr/stdout.

Needs an OpenSSL 3.5+ client to have any chance of negotiating ML-DSA —
same constraint the rest of this repo already works around (see
`servers/python/README.md`), so these scripts will run inside a
`python:3.13-slim-trixie`-equivalent container (or any other OpenSSL
3.5+-linked image) rather than assuming host OpenSSL is new enough.
