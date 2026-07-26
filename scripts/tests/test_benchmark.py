"""Handshake-timing benchmark against the running TLS servers.

Runs once per language (python, java, javascript). Not a strict pass/fail
perf gate (timing is hardware-dependent) — records min/mean/median/max/stdev
over repeated handshakes to results/metrics/handshake_benchmark_{language}.json
for comparison across runs/languages. Run with `pytest -s` to also see the
summary line.
"""

import json
import socket
import ssl
import statistics
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
METRICS_DIR = REPO_ROOT / "results" / "metrics"
REPEATS = 20


def _time_one_handshake(host, port):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    start = time.perf_counter()
    with socket.create_connection((host, port), timeout=5) as sock:
        with ctx.wrap_socket(sock, server_hostname=host):
            pass
    return time.perf_counter() - start


def test_handshake_timing_benchmark(require_live_server, server_address, language):
    host, port = server_address
    timings = [_time_one_handshake(host, port) for _ in range(REPEATS)]

    summary = {
        "ml_dsa_level": "44",
        "language": language,
        "repeats": REPEATS,
        "seconds": {
            "min": min(timings),
            "max": max(timings),
            "mean": statistics.mean(timings),
            "median": statistics.median(timings),
            "stdev": statistics.stdev(timings) if REPEATS > 1 else 0.0,
        },
    }

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    results_file = METRICS_DIR / f"handshake_benchmark_{language}.json"
    results_file.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"\n{language} handshake benchmark ({REPEATS} runs): "
        f"mean={summary['seconds']['mean'] * 1000:.1f}ms "
        f"min={summary['seconds']['min'] * 1000:.1f}ms "
        f"max={summary['seconds']['max'] * 1000:.1f}ms"
    )

    assert all(t > 0 for t in timings)
