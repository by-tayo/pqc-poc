# Metrics schema

One row per test run in `results/metrics/*.csv`. Suggested columns:

| Column                  | Description                                              |
|-------------------------|------------------------------------------------------------|
| date                     | ISO date of the run                                        |
| language                 | python / java / js                                         |
| algorithm                | ml-dsa-44 / ml-dsa-65 / ml-dsa-87 / baseline (rsa2048, ecdsa-p256, ...) |
| scenario                 | compatibility / performance / validation / issue / renew / revoke |
| public_key_bytes         | size of the public key                                      |
| private_key_bytes        | size of the private key file                                 |
| signature_bytes          | size of a single signature                                   |
| cert_bytes               | size of server.pem (leaf cert)                               |
| chain_bytes              | size of full chain, if applicable                            |
| handshake_bytes_total    | total bytes exchanged during the TLS handshake (from pcap)   |
| handshake_time_ms        | wall-clock time from ClientHello to Finished                 |
| client_cpu_ms            | client-side CPU time spent in handshake                      |
| server_cpu_ms            | server-side CPU time spent in handshake                      |
| round_trips              | number of round trips observed in the handshake              |
| tls_version              | negotiated TLS version                                       |
| kem_group                | negotiated key exchange group (e.g. X25519MLKEM768)          |
| notes                    | free text                                                     |

Raw per-run data goes in `results/metrics/`; written summaries/narratives go
in `results/performance/`.
