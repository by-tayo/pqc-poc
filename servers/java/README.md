# Java TLS/mTLS server

Bare TLS 1.3 (`javax.net.ssl.SSLServerSocket`) - no HTTP layer beyond a
fixed `200 OK` response so `curl`/`openssl s_client` have something to
receive.

- `TlsServer.java` / `TlsClient.java` - server-auth only, port 8443.
- `MtlsServer.java` / `MtlsClient.java` - client cert required and
  verified, port 8444.
- `CertUtil.java` - shared PEM loading and in-memory BCFKS keystore
  assembly used by all four entry points.

## Compatibility finding: stock JDK cannot serve ML-DSA over TLS

Tested against `eclipse-temurin:25-jdk` (JDK 25, current LTS):

- JCA-level ML-DSA support is complete - `KeyFactory`, `Signature`, and
  `KeyPairGenerator` all work for ML-DSA-44/65/87 (JEP 497).
- Even with a correctly-loaded key, **JSSE (the TLS stack) fails the
  handshake**: `sun.security.ssl.X509Authentication` only recognizes
  EC/EdDSA/RSA/RSASSA-PSS cert types when selecting a certificate, so it
  never considers the ML-DSA one. The handshake dies with
  `SSLHandshakeException: (handshake_failure) No available authentication
  scheme`.

So: JDK 25 cannot terminate an ML-DSA TLS connection today, full stop,
regardless of how the key/keystore is built.

## The fix: JDK 21 + BouncyCastle

This server uses **JDK 21** (LTS) with **BouncyCastle 1.85**
(`bcprov-jdk18on`, `bcpkix-jdk18on`, `bctls-jdk18on`), registering BC's
own JSSE-compatible TLS provider (`BCJSSE`) instead of `SunJSSE`. Two
things had to be worked out to make this actually negotiate a handshake:

1. **Key loading.** BC's `PEMParser` + `JcaPEMKeyConverter`
   (`CertUtil.loadPrivateKey`/`loadCertificate`) parse the DigiCert Labs
   "seed + expandedKey" CHOICE-form key directly - no manual re-encoding
   needed.
2. **BCJSSE doesn't offer ML-DSA's still-draft TLS signature-scheme
   codepoints by default.** Fixed by setting
   `jdk.tls.client.SignatureSchemes` / `jdk.tls.server.SignatureSchemes`
   to explicitly include `mldsa44,mldsa65,mldsa87` - done in
   `CertUtil.setSignatureSchemes()`, called before any `SSLContext` is
   created, in every entry point.

## Config

- `ML_DSA_LEVEL` (default `44`) - which `certs/ml-dsa-<level>/` directory
  gets baked into the image (`--build-arg ML_DSA_LEVEL=65`).
- `MODE` (default `tls`) - `tls` or `mtls`, selects which server class the
  container runs.

## Run

```
docker compose build && docker compose up -d java-tls java-mtls
```

or directly:

```
docker build -f servers/java/Dockerfile -t pqc-poc-java --build-arg ML_DSA_LEVEL=44 .
docker run -p 8443:8443 -e MODE=tls pqc-poc-java
docker run -p 8444:8444 -e MODE=mtls pqc-poc-java
```

Multi-stage build: `maven:3.9-eclipse-temurin-21` compiles and resolves
dependencies (via `maven-dependency-plugin`'s `copy-dependencies`, not a
shaded/uber jar - shading BC's provider jars risks breaking their
`META-INF/services` registration), then the runtime stage copies just the
compiled classes + `lib/*.jar` onto a plain `eclipse-temurin:21-jre` image.

## Verifying it actually works

Same OpenSSL-version caveat as the other two servers - validate from an
OpenSSL 3.5+ container on the same Docker network, not your host tools.

**The JVM needs a couple of seconds to finish starting.** A connection
attempt right after `docker run`/`docker compose up` can get a plain
"connection refused" that has nothing to do with ML-DSA or certs - it just
means BC's provider registration and classloading haven't finished yet.
Wait a beat (or poll the container logs for `listening on`) before
concluding anything is actually broken.

## Known quirks

- `server.pem` has no SAN (EJBCA's `SERVER` profile limitation, see
  `certs/ml-dsa-44/README.md`), but that's irrelevant here - raw
  `SSLSocket`/`SSLServerSocket` usage doesn't do hostname verification
  unless you explicitly wire in a `HostnameVerifier` (an
  `HttpsURLConnection`-level feature), so neither client needs a
  workaround the way the Python/JS ones do.
- Both `server.pem` and `client.pem` are issued by the same EJBCA CA -
  both clients trust `ca-chain.pem`.
- Startup logs a handful of `WARNING: Ignoring unsupported entry in
  'jdk.tls.disabledAlgorithms'` lines from BC - harmless; BC just doesn't
  recognize a couple of legacy SHA-1 entries in the JDK's default security
  properties.
