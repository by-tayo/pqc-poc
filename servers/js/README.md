# JavaScript TLS/mTLS server

Bare TLS 1.3 (Node's built-in `tls` module, no extra dependencies) - no
HTTP layer beyond a fixed `200 OK` response so `curl`/`openssl s_client`
have something to receive.

- `tls_server.js` / `tls_client.js` - server-auth only, port 8443.
- `mtls_server.js` / `mtls_client.js` - client cert required and verified,
  port 8444.

Genuinely the easiest of the three languages here - Node 22/24 bundle
OpenSSL 3.5.7 and hand ML-DSA certs to the `tls` module with no extra
configuration.

## Config

- `ML_DSA_LEVEL` (default `44`) - which `certs/ml-dsa-<level>/` directory
  gets baked into the image (`--build-arg ML_DSA_LEVEL=65`).
- `MODE` (default `tls`) - `tls` or `mtls`, selects which server script the
  container runs.

## Run

```
docker compose build && docker compose up -d js-tls js-mtls
```

or directly:

```
docker build -f servers/js/Dockerfile -t pqc-poc-js --build-arg ML_DSA_LEVEL=44 .
docker run -p 8443:8443 -e MODE=tls pqc-poc-js
docker run -p 8444:8444 -e MODE=mtls pqc-poc-js
```

## Verifying it actually works

**Don't `apt-get install openssl` inside this container to check it** - the
Debian bookworm base image's system OpenSSL package is much older than the
3.5.7 Node bundles internally, and can't parse these certs. It'll look like
the server is broken when it isn't. Validate from an OpenSSL 3.5+
container (e.g. `python:3.13-slim-trixie`) on the same Docker network
instead:

```
docker run --rm --network <compose-network> python:3.13-slim-trixie \
  sh -c "printf 'GET / HTTP/1.1\r\nHost: pqc.poc.localhost\r\n\r\n' | \
  openssl s_client -connect js-tls:8443 -CAfile /certs/ml-dsa-44/server.pem -quiet"
```

## Known quirks

- `server.pem` has no `subjectAltName` - EJBCA's `SERVER` certificate
  profile didn't carry the requested `dNSName` through, even with
  `--altname` set on the end entity (see `certs/ml-dsa-44/README.md`) -
  both clients pass `checkServerIdentity: () => undefined` to work around
  it rather than relying on SAN matching.
- Both `server.pem` and `client.pem` are issued by the same EJBCA CA
  (`ca-chain.pem`) - both clients trust `ca-chain.pem` rather than
  `server.pem` directly.
