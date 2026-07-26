# Tests

pytest suite covering the project's four goals (README: Compatibility,
Performance, Validation, Lifecycle) against the ML-DSA-44 TLS servers
(`servers/`): cert/key material validation, live TLS handshake behavior,
and handshake-timing benchmarking. Live/benchmark tests run once per
language (python, java, javascript) against the ports `docker-compose.yml`
maps them to (443/8444/8544).

## Running

Start the servers first:

```
docker compose up --build
```

Then, for full coverage — handshake/benchmark tests need a live server
and an OpenSSL 3.5+ client, same reason as `scripts/verify_tls.sh`:

```
scripts/run_tests.sh
```

Or directly on the host for a quicker check. Cert-material tests run fine
there; ML-DSA-specific and live-server tests skip cleanly with a reason if
the host can't support them:

```
pip install -r scripts/tests/requirements.txt
pytest scripts/tests -v
```

Restrict to one language with `--language python|java|javascript`, or
point at a different host with `--server-host` (or `PQC_TEST_HOST` env
var) — e.g. `scripts/run_tests.sh --language java`.

## Files

- `conftest.py` — shared fixtures: cert/key paths, per-language server
  reachability, `--server-host`/`--language` options.
- `test_cert_material.py` — parses `server.pem`/`server.key` directly, no
  server required (not language-specific — same cert for all three).
- `test_tls_handshake.py` — live handshake, TLS version, verify on/off,
  hostname (mis)match.
- `test_benchmark.py` — repeated-handshake timing, written to
  `results/metrics/handshake_benchmark_{language}.json`.
