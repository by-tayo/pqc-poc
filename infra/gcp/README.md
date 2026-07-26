# GCP cross-region test — Singapore ↔ Tokyo

Real ML-DSA TLS/mTLS handshakes between two Compute Engine VMs in
different countries, over the actual public internet — not localhost,
not same-machine loopback. This is what the local Docker work
(`servers/*/README.md`) and the EJBCA CA (`infra/ejbca/README.md`)
were building toward: a real performance comparison across ML-DSA-44/65/87
under real network latency.

Driven entirely through the GCP Console + Cloud Shell (not this repo's
local machine) — deliberately hands-on rather than scripted, since the
point was building real GCP operational experience alongside the data.

## Topology

- **Tokyo** (`pqc-tokyo-server`, `asia-northeast1-b`) — runs the TLS/mTLS
  server, one language (Python) at a time.
- **Singapore** (`pqc-singapore-client`, `asia-southeast1-a`) — runs the
  client, connects to Tokyo's external IP.
- EJBCA itself stays local (this machine) — not deployed to GCP. Only the
  already-issued cert files travel to the VMs; no live connection back to
  EJBCA is needed. See "Why EJBCA doesn't run on GCP" below.

## Prerequisites: project + billing

Cloud Shell's default project is a restricted trial project
(`billingEnabled: false`, ID looks like `project-<uuid>`) — not usable for
Compute Engine. Create a real one:

```bash
gcloud projects create pqc-poc-gcp --name="pqc-poc"
gcloud config set project pqc-poc-gcp
```

Check for an existing billing account, link it:

```bash
gcloud billing accounts list
gcloud billing projects link pqc-poc-gcp --billing-account=<ACCOUNT_ID>
gcloud billing projects describe pqc-poc-gcp   # confirm billingEnabled: true
```

**Free trial caveat that cost us a round of confusion:** the Console's
Billing → Overview page can say "Free trial account" even when the trial
window has already expired — that label doesn't mean credit remains.
Check Billing → **Credits** specifically for the actual start/end dates
before assuming anything is covered. In our case the trial had ended
months before we started (real charges applied, correctly, to a valid
card on the linked billing account — a couple cents/hour for `e2-small`
VMs, non-issue cost-wise, just worth knowing going in).

Also unrelated to the above: GCP's *Always Free* perpetual tier **is**
region-restricted to a few US regions, but that's a completely different
thing from trial credit, and doesn't apply once a real billing account is
linked. Singapore/Tokyo work fine on a paying (or trial-credit) account.

Enable the API:

```bash
gcloud services enable compute.googleapis.com --project=pqc-poc-gcp
```

## Creating the VMs

```bash
gcloud compute instances create pqc-tokyo-server \
  --project=pqc-poc-gcp \
  --zone=asia-northeast1-b \
  --machine-type=e2-small \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --tags=pqc-test

gcloud compute instances create pqc-singapore-client \
  --project=pqc-poc-gcp \
  --zone=asia-southeast1-a \
  --machine-type=e2-small \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --tags=pqc-test
```

Notes on these choices:
- **Container-Optimized OS** (`cos-stable`/`cos-cloud`) — ships Docker
  pre-installed, nothing else to set up. Tradeoff: **no `git`, no package
  manager, no Python** on the host itself — everything has to run inside
  a container, and files have to arrive via `scp`, not `git clone`.
- **`e2-small`**, not `e2-micro` — enough headroom to run Docker + Python
  without memory pressure, still cheap.
- **External IPs are deliberate**, not an oversight. The goal is measuring
  *real* internet-routed latency between countries. Using GCP's internal
  networking instead would ride Google's private backbone between
  regions — much faster than the public internet, and not representative
  of a real client/server pair.
- `asia-northeast1-a` hit `ZONE_RESOURCE_POOL_EXHAUSTED` for us (transient
  capacity issue, unrelated to billing/quota) — `-b` worked. If a zone is
  full, try a sibling zone in the same region before assuming anything is
  wrong with the account.

Resulting IPs — real values redacted below (this repo is public); note
each `gcloud compute instances create`/`describe` call prints your own:

| VM | Internal IP | External IP |
|---|---|---|
| `pqc-tokyo-server` | `<TOKYO_INTERNAL_IP>` | `<TOKYO_EXTERNAL_IP>` |
| `pqc-singapore-client` | `<SINGAPORE_INTERNAL_IP>` | `<SINGAPORE_EXTERNAL_IP>` |

## Firewall rules

Scoped tightly — only the specific test port, only from Singapore's exact
IP, nothing open to the wider internet:

```bash
# TLS
gcloud compute firewall-rules create allow-pqc-tls-from-singapore \
  --project=pqc-poc-gcp \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:8443 \
  --source-ranges=<SINGAPORE_EXTERNAL_IP>/32 \
  --target-tags=pqc-test

# mTLS (needed before the mTLS pass - not yet created as of the TLS-only results below)
gcloud compute firewall-rules create allow-pqc-mtls-from-singapore \
  --project=pqc-poc-gcp \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:8444 \
  --source-ranges=<SINGAPORE_EXTERNAL_IP>/32 \
  --target-tags=pqc-test
```

SSH (port 22) is already open by default in GCP's default network — no
extra rule needed for that.

## Getting files onto the VMs

Since COS has no `git`, the flow is: **upload into Cloud Shell** (from
this repo checkout, via Cloud Shell's ⋮ menu → Upload), **then `scp` from
Cloud Shell to each VM** with `gcloud compute scp`. Cloud Shell is a
separate environment from both your local machine and the VMs — it has
no access to local files directly, and the VMs have no access to
anything except what's explicitly copied to them.

Per ML-DSA level, minimal file set:

**Tokyo needs:**
- `servers/python/tls_server.py` (once — same script handles all levels
  via `ML_DSA_LEVEL`)
- `certs/ml-dsa-<level>/server.pem`
- `certs/ml-dsa-<level>/server.key`

**Singapore needs:**
- `servers/python/tls_client.py` (once, but see the two edits below)
- `certs/ml-dsa-<level>/ca-chain.pem`

```bash
# from Cloud Shell, after uploading the files there
gcloud compute scp tls_server.py server.pem server.key pqc-tokyo-server:~/ --zone=asia-northeast1-b
gcloud compute scp tls_client.py ca-chain.pem pqc-singapore-client:~/ --zone=asia-southeast1-a
```

### Two edits `tls_client.py` needs for this test specifically

Not needed for local Docker testing (where it's always `localhost`), but
required here:

1. **`HOST`** — change from `"localhost"` to Tokyo's real external IP
   (redacted here, see the table above — yours will be printed when you
   create the VM). Otherwise the client tries to connect to itself.
2. **Handshake timing** — added `time.perf_counter()` immediately before
   and after `ctx.wrap_socket(...)`, printing the delta in milliseconds.
   Without this, `time docker run ...` measures container-startup
   overhead (~1 second) far more than the actual handshake (~150ms) —
   completely swamping the signal you actually care about.

Current full `tls_client.py` used for these tests:

```python
import os
import ssl
import socket
import time

CERT_DIR = f"/certs/ml-dsa-{os.environ.get('ML_DSA_LEVEL', '44')}"
HOST = "<TOKYO_EXTERNAL_IP>"  # your VM's real external IP goes here
PORT = 8443


def main():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cafile=f"{CERT_DIR}/ca-chain.pem")
    ctx.check_hostname = False

    with socket.create_connection((HOST, PORT)) as sock:
        t0 = time.perf_counter()
        with ctx.wrap_socket(sock, server_hostname="pqc.poc.localhost") as ssock:
            t1 = time.perf_counter()
            print(f"handshake OK: {ssock.version()} {ssock.cipher()}")
            print(f"handshake time: {(t1 - t0) * 1000:.2f} ms")
            ssock.sendall(b"GET / HTTP/1.1\r\nHost: pqc.poc.localhost\r\n\r\n")
            print(ssock.recv(4096).decode(errors="replace"))


if __name__ == "__main__":
    main()
```

Edited this via Cloud Shell's graphical Editor (⋮ menu area, "Open
Editor" button) rather than pasting into the terminal — see the
paste-corruption gotcha below for why.

## Running the TLS test, per level (Python)

**On Tokyo** — arrange the cert, (re)start the server pointed at the
right level:

```bash
gcloud compute ssh pqc-tokyo-server --zone=asia-northeast1-b
```

```bash
mkdir -p certs/ml-dsa-<level>
cp server.pem server.key certs/ml-dsa-<level>/
docker rm -f tls-server
docker run -d --name tls-server -p 8443:8443 -e ML_DSA_LEVEL=<level> \
  -v ~/tls_server.py:/py/tls_server.py -v ~/certs:/certs \
  python:3.13-slim-trixie python3 /py/tls_server.py
docker logs tls-server
docker inspect tls-server --format='{{.Config.Env}}'   # confirm ML_DSA_LEVEL actually took
```

**On Singapore** — arrange the cert, run 5 timed handshakes:

```bash
gcloud compute ssh pqc-singapore-client --zone=asia-southeast1-a
```

```bash
mkdir -p certs/ml-dsa-<level>
cp ca-chain.pem certs/ml-dsa-<level>/

cat > time_test_<level>.sh << 'EOF'
for i in 1 2 3 4 5; do
  echo "=== run $i ==="
  time docker run --rm -e ML_DSA_LEVEL=<level> \
    -v ~/tls_client.py:/py/tls_client.py -v ~/certs:/certs \
    python:3.13-slim-trixie python3 /py/tls_client.py
done
EOF
cat time_test_<level>.sh   # verify before running - see gotcha below
bash time_test_<level>.sh
```

## Results — Python TLS, 5 runs per level

| Run | ML-DSA-44 | ML-DSA-65 | ML-DSA-87 |
|---|---|---|---|
| 1 | 151.34 ms | 160.21 ms | 162.11 ms |
| 2 | 156.25 ms | 157.18 ms | 154.89 ms |
| 3 | 148.65 ms | 152.47 ms | 156.83 ms |
| 4 | 149.97 ms | 157.44 ms | 149.71 ms |
| 5 | 153.75 ms | 159.28 ms | 166.82 ms |
| **Average** | **~152.0 ms** | **~157.3 ms** | **~158.1 ms** |

**Finding:** handshake time increases with security level - ML-DSA-44
fastest, ML-DSA-87 slowest, consistent with larger keys/signatures at
higher levels meaning more bytes transmitted and more computation per
handshake. The 44→65 jump (+5.3ms) is larger than 65→87 (+0.8ms), tracking
with how those levels' actual parameter sizes scale.

## Running the mTLS test, per level (Python)

Same shape as TLS, using `mtls_server.py`/`mtls_client.py` (port 8444)
instead of `tls_server.py`/`tls_client.py`, plus the client identity.

**Tokyo needs**, additionally: `ca-chain.pem` (to verify Singapore's
client cert).

**Singapore needs**, additionally: `client.pem`, `client.key`.

Both `tls_client.py` and `mtls_client.py` read `HOST` from an environment
variable now (defaulting to `localhost`), not a hardcoded IP - pass it at
`docker run` time with `-e HOST=<tokyo-external-ip>` instead of editing
the file. Keeps the real IP out of the repo entirely. `mtls_client.py`
also has the same timing instrumentation as `tls_client.py`, added the
same way (Cloud Shell's graphical Editor, not terminal paste).

```bash
# Tokyo
cp ca-chain.pem certs/ml-dsa-<level>/
docker rm -f mtls-server
docker run -d --name mtls-server -p 8444:8444 -e ML_DSA_LEVEL=<level> \
  -v ~/mtls_server.py:/py/mtls_server.py -v ~/certs:/certs \
  python:3.13-slim-trixie python3 /py/mtls_server.py
docker inspect mtls-server --format='{{.Config.Env}}'   # confirm ML_DSA_LEVEL took
```

```bash
# Singapore - negative test first (no client cert, expect rejection).
# Note: must actually send/receive data, not just check whether
# wrap_socket() raised - under TLS 1.3 the server's rejection can surface
# slightly after wrap_socket() returns "successfully", so a naive
# try/except around wrap_socket() alone gives a false "connected" result.
cp client.pem client.key certs/ml-dsa-<level>/
docker run --rm -v ~/certs:/certs python:3.13-slim-trixie python3 -c "
import ssl, socket
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.load_verify_locations(cafile='/certs/ml-dsa-<level>/ca-chain.pem')
ctx.check_hostname = False
sock = socket.create_connection(('<TOKYO_EXTERNAL_IP>', 8444))
try:
    ssock = ctx.wrap_socket(sock, server_hostname='pqc.poc.localhost')
    ssock.sendall(b'GET / HTTP/1.1\r\nHost: pqc.poc.localhost\r\n\r\n')
    data = ssock.recv(4096)
    print('UNEXPECTED: got a real response:', data[:50]) if data else print('correctly rejected: connection closed, no data')
except (ssl.SSLError, ConnectionResetError, BrokenPipeError, OSError) as e:
    print('correctly rejected:', repr(e))
"

# Singapore - positive test (with client cert), timed, 5 runs
cat > mtime_test_<level>.sh << 'EOF'
for i in 1 2 3 4 5; do
  echo "=== run $i ==="
  time docker run --rm -e ML_DSA_LEVEL=<level> -e HOST=<TOKYO_EXTERNAL_IP> \
    -v ~/mtls_client.py:/py/mtls_client.py -v ~/certs:/certs \
    python:3.13-slim-trixie python3 /py/mtls_client.py
done
EOF
cat mtime_test_<level>.sh
bash mtime_test_<level>.sh
```

Negative test confirmed correctly rejecting for all three levels (Tokyo's
own log independently confirms it too:
`[SSL: PEER_DID_NOT_RETURN_A_CERTIFICATE]`, or from the client side,
`TLSV13_ALERT_CERTIFICATE_REQUIRED`).

## Results — Python mTLS, 5 runs per level

| Run | ML-DSA-44 | ML-DSA-65 | ML-DSA-87 |
|---|---|---|---|
| 1 | 157.40 ms | 166.29 ms | 155.49 ms |
| 2 | 168.31 ms | 164.42 ms | 157.37 ms |
| 3 | 159.30 ms | 161.43 ms | 163.22 ms |
| 4 | 156.96 ms | 176.38 ms | 160.67 ms |
| 5 | 160.06 ms | 162.32 ms | 170.32 ms |
| **Average** | **~160.4 ms** | **~166.2 ms** | **~161.4 ms** |

## Python: TLS vs. mTLS — full comparison

| | TLS | mTLS | Δ |
|---|---|---|---|
| ML-DSA-44 | ~152.0 ms | ~160.4 ms | +8.4 ms |
| ML-DSA-65 | ~157.3 ms | ~166.2 ms | +8.9 ms |
| ML-DSA-87 | ~158.1 ms | ~161.4 ms | +3.3 ms |

mTLS consistently costs more than plain TLS, as expected (extra round of
client-side signing/verification on top of the server's own). The
44/65 delta (+8-9ms) is noticeably larger than 87's (+3.3ms) - could be
a real effect, but with only 5 runs per cell this is exactly the kind of
thing that needs more repetitions to distinguish from network jitter
rather than take at face value.

## Adding another language: JavaScript

Certs are already on both VMs for all three levels (language-agnostic
PEM/key files) - only the JS source files needed transferring. Same
upload-to-Cloud-Shell-then-scp process, no cert re-transfer needed:

```bash
gcloud compute scp tls_server.js mtls_server.js pqc-tokyo-server:~/ --zone=asia-northeast1-b
gcloud compute scp tls_client.js mtls_client.js pqc-singapore-client:~/ --zone=asia-southeast1-a
```

`tls_client.js`/`mtls_client.js` needed the same two additions as their
Python counterparts (`HOST` from an env var, handshake timing) - but
structured a bit differently to get a fair, comparable measurement: split
the raw TCP connect (`net.connect`) from the TLS handshake
(`tls.connect({socket: rawSocket, ...})`), timing only the latter with
`process.hrtime.bigint()`. `tls.connect()` alone would otherwise bundle
TCP connect time into the "handshake" number, which the Python version
deliberately avoids by doing the same two-step split with
`socket.create_connection()` then `ctx.wrap_socket()`.

Server-side commands, per level:

```bash
# Tokyo - TLS
docker rm -f tls-server
docker run -d --name tls-server -p 8443:8443 -e ML_DSA_LEVEL=<level> \
  -v ~/tls_server.js:/app/tls_server.js -v ~/certs:/certs \
  node:22-slim node /app/tls_server.js

# Tokyo - mTLS
docker rm -f mtls-server
docker run -d --name mtls-server -p 8444:8444 -e ML_DSA_LEVEL=<level> \
  -v ~/mtls_server.js:/app/mtls_server.js -v ~/certs:/certs \
  node:22-slim node /app/mtls_server.js
```

Client-side (Singapore), same shape as Python's timing scripts:

```bash
cat > jtime_test_<level>.sh << 'EOF'
for i in 1 2 3 4 5; do
  echo "=== run $i ==="
  time docker run --rm -e ML_DSA_LEVEL=<level> -e HOST=<TOKYO_EXTERNAL_IP> \
    -v ~/tls_client.js:/app/tls_client.js -v ~/certs:/certs \
    node:22-slim node /app/tls_client.js
done
EOF
bash jtime_test_<level>.sh   # same pattern for mtls_client.js -> mjtime_test_<level>.sh
```

Negative test (no client cert) needed a small standalone script rather
than reusing `tls_client.js`, since that one doesn't load a client cert at
all:

```bash
cat > negative_test.js << 'EOF'
const tls = require('tls');
const fs = require('fs');
const socket = tls.connect({
  host: '<TOKYO_EXTERNAL_IP>',
  port: 8444,
  ca: fs.readFileSync('/certs/ml-dsa-<level>/ca-chain.pem'),
  checkServerIdentity: () => undefined,
}, () => {
  socket.write('GET / HTTP/1.1\r\nHost: pqc.poc.localhost\r\n\r\n');
});
socket.on('data', (data) => {
  console.log('UNEXPECTED: got a response:', data.toString().slice(0, 50));
  socket.end();
});
socket.on('error', (err) => {
  console.log('correctly rejected:', err.message);
});
EOF
docker run --rm -v ~/certs:/certs -v ~/negative_test.js:/app/negative_test.js node:22-slim node /app/negative_test.js
```

Confirmed correctly rejecting for all three levels (`tlsv13 alert
certificate required`, same as Python's server-side log line).

### Results — JavaScript TLS, 5 runs per level

| Run | ML-DSA-44 | ML-DSA-65 | ML-DSA-87 |
|---|---|---|---|
| 1 | 100.57 ms | 97.73 ms | 100.37 ms |
| 2 | 96.60 ms | 95.63 ms | 92.55 ms |
| 3 | 92.79 ms | 93.38 ms | 100.86 ms |
| 4 | 97.15 ms | 95.10 ms | 100.42 ms |
| 5 | 93.08 ms | 96.10 ms | 97.35 ms |
| **Average** | **~96.0 ms** | **~95.6 ms** | **~98.3 ms** |

### Results — JavaScript mTLS, 5 runs per level

| Run | ML-DSA-44 | ML-DSA-65 | ML-DSA-87 |
|---|---|---|---|
| 1 | 97.66 ms | 98.07 ms | 98.62 ms |
| 2 | 99.72 ms | 98.76 ms | 98.79 ms |
| 3 | 97.32 ms | 99.56 ms | 99.38 ms |
| 4 | 100.13 ms | 99.95 ms | 100.41 ms |
| 5 | 100.15 ms | 98.66 ms | 98.77 ms |
| **Average** | **~99.0 ms** | **~99.0 ms** | **~99.2 ms** |

### Cross-language comparison (TLS)

| | ML-DSA-44 | ML-DSA-65 | ML-DSA-87 |
|---|---|---|---|
| Python | ~152.0 ms | ~157.3 ms | ~158.1 ms |
| JavaScript | ~96.0 ms | ~95.6 ms | ~98.3 ms |

**Finding:** JavaScript is consistently faster than Python across all
three levels (roughly 55-60ms less per handshake), and JS's numbers
barely move between security levels while Python's show a clearer upward
trend. Plausibly down to how Node's TLS/OpenSSL bindings differ
internally from Python's `ssl` module - not investigated further here,
but a genuine, repeatable cross-language difference rather than noise
(the gap is far larger than the run-to-run variance within either
language).

## Adding the third language: Java

Java needs the full Maven project on **both** VMs (not just scripts) -
`pom.xml` plus all 5 `.java` files under `src/main/java/com/pqcpoc/` -
since there's no way to build "just the client part"; each side builds
its own copy and runs whichever class it needs
(`TlsServer`/`MtlsServer` on Tokyo, `TlsClient`/`MtlsClient` on
Singapore) from the same compiled output.

`HOST` was already an environment variable in `TlsClient.java`/
`MtlsClient.java` (no hardcoded-IP cleanup needed, unlike the Python/JS
clients originally). Only addition needed: timing around
`socket.startHandshake()` with `System.nanoTime()`. Unlike JS, no
restructuring was needed - `createSocket()` already separates the TCP
connect from the explicit `startHandshake()` call.

```bash
# Organize into Maven's expected directory structure, in Cloud Shell
mkdir -p java-project/src/main/java/com/pqcpoc
mv pom.xml java-project/
mv CertUtil.java TlsServer.java MtlsServer.java TlsClient.java MtlsClient.java \
  java-project/src/main/java/com/pqcpoc/

# Push the whole project to BOTH VMs
gcloud compute scp --recurse java-project pqc-tokyo-server:~/java-project --zone=asia-northeast1-b
gcloud compute scp --recurse java-project pqc-singapore-client:~/java-project --zone=asia-southeast1-a
```

Build on each VM (takes ~20-30s, pulls BouncyCastle dependencies):

```bash
docker run --rm -v ~/java-project:/build -w /build maven:3.9-eclipse-temurin-21 mvn -q -B package
```

Server-side, per level (note both `-v ~/java-project:/app` *and*
`-v ~/certs:/certs` are required - missing the certs mount was a mistake
made once here, producing a `FileNotFoundException` for `server.key`):

```bash
docker rm -f tls-server mtls-server
docker run -d --name tls-server -p 8443:8443 -e ML_DSA_LEVEL=<level> \
  -v ~/java-project:/app -v ~/certs:/certs -w /app \
  maven:3.9-eclipse-temurin-21 java -cp target/classes:target/lib/* com.pqcpoc.TlsServer

docker run -d --name mtls-server -p 8444:8444 -e ML_DSA_LEVEL=<level> \
  -v ~/java-project:/app -v ~/certs:/certs -w /app \
  maven:3.9-eclipse-temurin-21 java -cp target/classes:target/lib/* com.pqcpoc.MtlsServer
```

Client-side (Singapore), timed:

```bash
cat > jatime_test_<level>.sh << 'EOF'
for i in 1 2 3 4 5; do
  echo "=== run $i ==="
  time docker run --rm -e ML_DSA_LEVEL=<level> -e HOST=<TOKYO_EXTERNAL_IP> \
    -v ~/java-project:/app -v ~/certs:/certs -w /app \
    maven:3.9-eclipse-temurin-21 java -cp target/classes:target/lib/* com.pqcpoc.TlsClient
done
EOF
bash jatime_test_<level>.sh   # same pattern for MtlsClient -> majtime_test_<level>.sh
```

Negative test: running `TlsClient` (no client cert) against the mTLS
port (`-e PORT=8444`) is itself the test - it should throw
`TlsFatalAlertReceived: certificate_required(116)` when reading the
response, not when the handshake call itself returns (same TLS 1.3
post-handshake-alert nuance noted in the Python section - confirmed
identically here, just via a Java exception instead of a Python one).

### Gotchas specific to Java

- **`scp --recurse` can double-nest** if the destination directory
  already exists on the remote - ended up with
  `java-project/java-project/pom.xml` once. If `mvn package` says
  "no POM in this directory," check for this with
  `find java-project -name pom.xml` before assuming the transfer failed.
- **First run after a fresh `docker run --rm` batch is consistently
  slower** (seen 800ms+ on run 1 vs ~300ms for runs 2-5) - the
  BouncyCastle jars total ~13MB, and the first read pays real disk I/O
  that the OS page-caches for subsequent runs, even though each run is a
  genuinely fresh JVM process. Treated as a warm-up: discarded run 1 and
  did a full clean re-run of all 5 for every level/mode below, rather
  than mixing a 4-run set with 5-run ones elsewhere.

### Results — Java TLS, 5 runs per level (post warm-up)

| Run | ML-DSA-44 | ML-DSA-65 | ML-DSA-87 |
|---|---|---|---|
| 1 | 297.58 ms | 304.38 ms | 315.41 ms |
| 2 | 297.52 ms | 300.33 ms | 285.29 ms |
| 3 | 294.56 ms | 292.88 ms | 293.21 ms |
| 4 | 295.35 ms | 337.82 ms | 294.11 ms |
| 5 | 281.79 ms | 278.32 ms | 271.01 ms |
| **Average** | **~293.4 ms** | **~302.7 ms** | **~291.8 ms** |

### Results — Java mTLS, 5 runs per level (post warm-up)

| Run | ML-DSA-44 | ML-DSA-65 | ML-DSA-87 |
|---|---|---|---|
| 1 | 336.20 ms | 300.37 ms | 316.58 ms |
| 2 | 322.06 ms | 323.20 ms | 302.76 ms |
| 3 | 337.85 ms | 290.50 ms | 296.80 ms |
| 4 | 323.45 ms | 307.72 ms | 324.87 ms |
| 5 | 308.43 ms | 322.32 ms | 343.06 ms |
| **Average** | **~325.6 ms** | **~308.8 ms** | **~316.8 ms** |

## Full cross-language comparison — all three languages, both modes

| | ML-DSA-44 TLS | ML-DSA-65 TLS | ML-DSA-87 TLS | ML-DSA-44 mTLS | ML-DSA-65 mTLS | ML-DSA-87 mTLS |
|---|---|---|---|---|---|---|
| Python | 152.0 ms | 157.3 ms | 158.1 ms | 160.4 ms | 166.2 ms | 161.4 ms |
| JavaScript | 96.0 ms | 95.6 ms | 98.3 ms | 99.0 ms | 99.0 ms | 99.2 ms |
| Java | 293.4 ms | 302.7 ms | 291.8 ms | 325.6 ms | 308.8 ms | 316.8 ms |

**Headline findings:**
- **JavaScript is fastest across the board**, consistently, and barely
  affected by security level or TLS-vs-mTLS.
- **Python is in the middle**, with the clearest level-dependent trend of
  the three (handshake time rises with security level, most visible in
  its TLS numbers).
- **Java is slowest by a wide margin** (roughly 2-3x Python, ~3x JS) -
  almost certainly reflects BCJSSE (BouncyCastle's third-party pure-Java
  TLS provider, required since stock JSSE can't do ML-DSA at all) rather
  than the JVM itself being inherently slow. Not investigated further,
  but worth remembering this benchmarks BCJSSE specifically, not "Java."
- **mTLS consistently costs more than plain TLS** in every language, as
  expected (client-side signing/verification on top of the server's own),
  though the size of that overhead varies a lot by language: JS ~3ms,
  Python ~3-9ms, Java as much as ~32ms.
- All numbers here are from 5 runs per cell - enough to see clear,
  consistent cross-language differences (far larger than the
  run-to-run variance within any one language/level), but not enough to
  fully trust the smaller level-to-level deltas within a single language
  (e.g. Python's 87 mTLS dropping below 65's). A larger repetition count
  would be needed to separate real level-dependent effects from network
  jitter at that finer grain.

## Why EJBCA doesn't run on GCP (a decision, not an oversight)

Locking down EJBCA's own Admin Web turned out to hit a real, deeper issue:
the WildFly TLS listener (`TLS_SETUP_ENABLED=simple`) can't actually
process an incoming client certificate at all — presenting one causes an
immediate connection failure (`unexpected eof`, matching browser
`ERR_EMPTY_RESPONSE`), independent of which cert or browser. Confirmed
directly with `openssl s_client`, not just through browser testing.
Fixing this properly means digging into WildFly's truststore
configuration - real work, not attempted.

Given that, keeping EJBCA local (never exposed on a public GCP IP) avoids
needing that fix at all - the cross-region test only needs the
already-issued cert files, not a live connection back to EJBCA. If EJBCA
itself is ever deployed to GCP later, this becomes a real blocker again.

## Gotchas encountered running this for real

- **`ZONE_RESOURCE_POOL_EXHAUSTED`** is a transient capacity issue for
  that specific zone/machine-type combination — unrelated to
  billing/quota. Try a sibling zone (`-a`/`-b`/`-c` in the same region).
- **Cloud Shell's active project can silently reset** back to the default
  trial project (e.g. after a session timeout) - always check
  `gcloud config get-value project` before anything billing-sensitive,
  especially after a break.
- **It's easy to run VM-intended commands in Cloud Shell by mistake** -
  check the shell prompt before running anything (`pqc-tokyo-server` /
  `pqc-singapore-client` = actually on the VM; `cloudshell` = not). This
  bit us once - a `docker run` meant for Tokyo actually started in Cloud
  Shell's own separate Docker environment instead.
- **Multi-line pastes into web terminals (Cloud Shell, SSH sessions)
  reliably corrupt on longer content** - characters silently dropped or
  merged (`ssock.recv(...)` became `ssoceplace"))` in one case). Always
  `cat` a file back after writing it via heredoc, before running anything
  that depends on it. For anything larger than a few lines, Cloud Shell's
  graphical Editor (⋮ menu → Open Editor) is far more reliable than
  terminal paste.
- **A dropped `-e` flag fails silently** - if `ML_DSA_LEVEL=65` got lost
  from a corrupted paste, the container would just default back to 44
  with no error, silently corrupting the comparison data. Always verify
  with `docker inspect <container> --format='{{.Config.Env}}'` after
  starting a level-specific container, not just that it started.
- **Free trial "account" label ≠ active trial credit** - check the actual
  dates under Billing → Credits, not just the Overview page's badge.

## Cleanup

Run once all TLS/mTLS passes and repetitions are done - both VMs bill by
the hour regardless of trial/real-money status:

```bash
gcloud compute instances delete pqc-tokyo-server --zone=asia-northeast1-b
gcloud compute instances delete pqc-singapore-client --zone=asia-southeast1-a
gcloud compute firewall-rules delete allow-pqc-tls-from-singapore
gcloud compute firewall-rules delete allow-pqc-mtls-from-singapore
```
