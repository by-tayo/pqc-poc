# Benchmark scripts

Handshake timing/CPU/byte-size measurement scripts (e.g. openssl s_client
timing, custom client/server instrumentation).

Repeated-handshake timing is now covered by
`scripts/tests/test_benchmark.py` (`scripts/run_tests.sh` to run it), once
per language, writing results to
`results/metrics/handshake_benchmark_{python,java,javascript}.json`.
CPU cost and bytes-on-wire measurement are not yet written.
