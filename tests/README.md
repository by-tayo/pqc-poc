# tests/

Multi-tool client-side verification that TLS and **mTLS** handshakes actually
work end-to-end, against every endpoint in the comparison matrix. This is
new and additive — see [How this relates to `scripts/tests/`](#how-this-relates-to-scriptstests)
below for how it differs from the existing pytest suite.

## The matrix

| Tool         | Language/runtime          | Status                                          |
|--------------|----------------------------|--------------------------------------------------|
| `openssl/`   | `openssl s_client`/`s_server` CLI | Not yet written — Phase 3                 |
| `python/`    | Python 3.13 (`ssl` stdlib) | Not yet written — Phase 3 (extends the pattern already proven in `scripts/tests/`, adds client-cert/mTLS coverage that doesn't exist there yet) |
| `nodejs/`    | Node 22/24 (`tls` stdlib) | Not yet written — Phase 3 (first client-side JS test in this repo; today `servers/js/` only has the *server*) |
| `java/`      | JDK 21 + BouncyCastle 1.85 (BCJSSE) | Not yet written — Phase 3 (adapts the recipe in `servers/java/README.md` from server role to client role — the highest-risk one) |
| `wireshark/` | `tshark`/`dumpcap`         | Not yet written — Phase 3 (`captures/wireshark/` is currently empty; `scripts/capture/README.md` has said "not yet written" since before this restructure) |

Each tool, once implemented, is exercised against every endpoint (Python,
Java, JS, and — once Phase 2 lands — Apache) × every available cert level
(ML-DSA-44 today; 65/87 once populated) × two scenarios: plain TLS
(server-auth only, the only thing this repo does today) and **mTLS**
(client presents a cert too — net-new, see `docs/test-cases.md`).

## How this relates to `scripts/tests/`

`scripts/tests/` (pytest, Python-only) is the existing **automated
regression suite** — cert material validation, live TLS handshake behavior,
and benchmark timing, run via `scripts/run_tests.sh` on every change. It
is TLS-only and stays exactly as-is; nothing here replaces it.

`tests/` is **additive**: the multi-tool (not just Python), mTLS-focused
verification the wider project roadmap needs — proving a human (or CI) can
actually pick up `openssl`, a Node script, a Java client, or Wireshark and
confirm a handshake with a *different* client than the one that happens to
be running the server. `scripts/tests/`'s Python client and `tests/python/`'s
client overlap in language only; `tests/python/` specifically covers the
client-certificate path `scripts/tests/` has never had.

## Roadmap

See the repo root `README.md`'s Roadmap section for the full six-phase
plan this folder is part of. Short version: this skeleton is Phase 1; the
actual test cases land in Phase 3, once Phase 2 gets mTLS working locally
(no point writing mTLS test cases against a server that doesn't do mTLS
yet).
