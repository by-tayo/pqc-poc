# tests/java/

Not yet written — Phase 3. **The highest-risk one of the five.**

`servers/java/README.md` documents, in detail, why stock JDK can't
terminate an ML-DSA TLS handshake as a *server*, and the fix: JDK 21 (not
25 — confirmed broken) + BouncyCastle 1.85
(`bcprov`/`bcpkix`/`bctls-jdk18on`) via the BCJSSE provider, plus setting
`jdk.tls.server.SignatureSchemes` / `jdk.tls.client.SignatureSchemes` to
include `mldsa44,mldsa65,mldsa87` **before** any `SSLContext` is created
(BCJSSE doesn't enable the still-draft ML-DSA codepoints by default).

This folder adapts that exact recipe to the **client** role instead:
`SSLContext.getInstance("TLS", "BCJSSE")` with a client-side
`KeyManagerFactory` loaded from a `BCFKS` keystore holding the client
cert/key, `TrustManagerFactory` pointed at `ca-chain.pem`, same
`SignatureSchemes` system properties set first. Nothing about this
combination (BCJSSE as client + client-cert auth + ML-DSA) has been
tried yet in this repo — expect this to take real debugging, not a
mechanical port of `servers/java/src/main/java/com/pqcpoc/TlsServer.java`.

Same JDK 21 + BouncyCastle 1.85 pin as the server; see `servers/java/pom.xml`
for exact Maven coordinates.
