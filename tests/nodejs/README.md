# tests/nodejs/

Not yet written — Phase 3.

The first **client-side** JS test in this repo — today `servers/js/`
only has the server half. Will use Node's built-in `tls` module
(`tls.connect({ cert, key, ca, ... })`), matching `servers/js/tls_server.js`'s
approach of relying entirely on Node's bundled OpenSSL (3.5.7 as of Node
22/24) rather than any extra PQC library. Covers plain TLS and mTLS
against each endpoint, same matrix as `tests/python/`.

Base image: Node 22 or 24 — confirmed working for ML-DSA in
`servers/js/README.md` ("Compatibility finding: it just works"). No
BouncyCastle-style workaround needed, unlike Java.
