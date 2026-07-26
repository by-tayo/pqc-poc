# Python TLS/mTLS server

Bare TLS 1.3 (`ssl` module, stdlib only, no extra dependencies) - no HTTP
layer beyond a fixed `200 OK` response so `curl`/`openssl s_client` have
something to receive.

- `tls_server.py` / `tls_client.py` - server-auth only, port 8443.
- `mtls_server.py` / `mtls_client.py` - client cert required and verified,
  port 8444.

## Why this runs in Docker

Host OpenSSL is almost certainly older than 3.5, and ML-DSA support only
landed in OpenSSL 3.5. `python:3.13-slim-trixie` ships OpenSSL 3.5.6 and
handles these certs with no extra provider - that's the only reason this
needs a container at all.

## Config

- `ML_DSA_LEVEL` (default `44`) - which `certs/ml-dsa-<level>/` directory
  gets baked into the image (`--build-arg ML_DSA_LEVEL=65`). Build-time,
  not runtime, since the image only ever carries one level's private key.
- `MODE` (default `tls`) - `tls` or `mtls`, selects which server script the
  container runs. Runtime env var - both modes can share one build.

## Run

```
docker compose build && docker compose up -d python-tls python-mtls
```

or directly:

```
docker build -f servers/python/Dockerfile -t pqc-poc-python --build-arg ML_DSA_LEVEL=44 .
docker run -p 8443:8443 -e MODE=tls pqc-poc-python
docker run -p 8444:8444 -e MODE=mtls pqc-poc-python
```

## Verifying it actually works

Your host `openssl`/`curl` almost certainly can't complete this handshake
either, for the same OpenSSL-version reason as above. Validate from another
OpenSSL 3.5+ container on the same Docker network instead, e.g.:

```
docker run --rm --network <compose-network> python:3.13-slim-trixie \
  sh -c "printf 'GET / HTTP/1.1\r\nHost: pqc.poc.localhost\r\n\r\n' | \
  openssl s_client -connect python-tls:8443 -CAfile /certs/ml-dsa-44/server.pem -quiet"
```

(mount `certs/` into that validator container too, or `curl --cacert` the
same way.)

## Known quirks

- `server.pem` has no `subjectAltName` - EJBCA's `SERVER` certificate
  profile didn't carry the requested `dNSName` through, even with
  `--altname` set on the end entity (see `certs/ml-dsa-44/README.md`) -
  both clients set `check_hostname = False` to work around it rather than
  relying on SAN matching.
- Both `server.pem` and `client.pem` are issued by the same EJBCA CA
  (`ca-chain.pem`) - both clients trust `ca-chain.pem` rather than
  `server.pem` directly.
- The server only catches `(ssl.SSLError, OSError)` around each
  connection deliberately - a client disconnecting mid-response
  (`BrokenPipeError` etc.) must not take the whole server down.
