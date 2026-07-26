# tests/python/

Not yet written — Phase 3.

Adds **client-certificate (mTLS)** coverage that `scripts/tests/` doesn't
have — every client context there is either `CERT_NONE` (permissive) or
configured only to verify the *server's* cert; nothing calls
`load_cert_chain()` on the client side. This folder is where that gets
added: `ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)` +
`ctx.load_cert_chain(certfile=client.pem, keyfile=client.key)` +
`ctx.load_verify_locations(cafile=ca-chain.pem)`, connecting to each
endpoint's mTLS-gated port (Apache's reverse-proxy vhost, once Phase 2
lands) and asserting the handshake succeeds with a client cert and fails
without one.

Same execution constraint as the rest of this repo: needs OpenSSL 3.5+,
so runs inside a `python:3.13-slim-trixie`-equivalent container via the
same pattern `scripts/run_tests.sh` already uses (host OpenSSL is
typically too old).
