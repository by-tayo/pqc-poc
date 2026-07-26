# tests/wireshark/

Not yet written — Phase 3. `captures/wireshark/` is currently empty
(`.gitkeep` only) and `scripts/capture/README.md` has said "tshark/dumpcap
automation... not yet written" since before this restructure — this is
genuinely greenfield, nothing to port from elsewhere in the repo.

Will automate: start a `tshark -i <iface> -f "tcp port <port>" -w
capture.pcapng` capture, trigger a handshake using one of the other
tools' clients (`tests/openssl/`, `tests/python/`, etc.), stop the
capture, then a verification pass (`tshark -r` or `pyshark`) asserting
things like TLS 1.3 negotiated, the expected group/signature scheme
observed on the wire, and — for mTLS captures — that a client Certificate
message is actually present.

Output should populate the richer fields `results/metrics/schema.md`
already documents but nothing currently emits: `handshake_bytes_total`,
`kem_group`, `round_trips`. Today's `results/metrics/handshake_benchmark_*.json`
only has timing stats — this is the piece that fills in the byte-level
data schema.md was written for.
