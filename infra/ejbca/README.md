# EJBCA — the PKI layer for pqc-poc

## Go/no-go result: **confirmed working**

Before building anything on top of EJBCA, the open question was whether
EJBCA **Community Edition** (free, open source) can actually issue ML-DSA
certificates, or whether that's gated to Enterprise. The only official
Keyfactor tutorial covering PQC (["Build a Post-Quantum Ready PKI with
Hybrid CAs"](https://docs.keyfactor.com/ejbca/9.3.2/tutorial-build-a-post-quantum-ready-pki))
explicitly uses an **EJBCA Enterprise 9.2+ trial**, which reads as a bad
sign at first glance.

It's a red herring for this project, though: that tutorial is specifically
about **hybrid/composite** CAs (dual classical+PQC signatures on one
cert) — that's the Enterprise-gated part. **Plain, single-algorithm
ML-DSA — exactly what this project uses — works in Community Edition.**
Verified end-to-end against `keyfactor/ejbca-ce:latest` (resolved to
**EJBCA 9.3.7** at verification time):

1. Generated an ML-DSA-44 key pair in a soft crypto token via the CLI.
2. Created a self-signed ML-DSA-44 root CA from that key (`ca init`).
3. Generated an ML-DSA-44 keypair + CSR with `openssl req` (needs OpenSSL
   3.5+, same constraint as the rest of this repo).
4. Added an end entity and issued a leaf certificate from that CSR,
   signed by the ML-DSA-44 CA (`ra addendentity` + `createcert`).
5. Validated the full chain: `openssl verify -CAfile ca.pem leaf.pem` →
   `OK`. `openssl x509 -text` on both certs shows `Signature Algorithm:
   ML-DSA-44` and `Public Key Algorithm: ML-DSA-44` throughout.

So: **EJBCA CE is the CA for this project, no Enterprise trial needed.**
The hybrid-CA tutorial stays relevant only as a reference if a future
phase wants composite classical+PQC certs, which is out of scope here.

## Bring it up

```bash
cp .env.example .env   # then fill in your own DB credentials — .env is gitignored
docker compose -f docker-compose.ejbca.yml up -d
```

WildFly takes 1-2 minutes to finish deploying on first boot. Watch for
`WFLYSRV0025: WildFly ... started` in `docker logs ejbca`.

The `ejbca-node1` service sets `DATABASE_USER`/`DATABASE_PASSWORD`
explicitly to match MariaDB's `MYSQL_USER`/`MYSQL_PASSWORD` - without
these, EJBCA falls back to its image-default credentials (`ejbca`/`ejbca`)
and fails to connect with a repeating `Access denied for user 'ejbca'`
error, even though both containers report as "running". If you ever see
that, this is why.

**This compose file has its own project name** (`name: pqc-poc-ejbca`),
deliberately different from `docker-compose.yml`'s (which defaults to the
directory name, `pqc-poc`). Without that, Compose treats both files as the
same project, and `docker compose down --remove-orphans` on the app stack
(no `-f`) will delete these containers as "orphans" of its own project -
lost this exact way once while switching between the two stacks. The
`mariadb-data` volume is pinned to its original name
(`pqc-poc_mariadb-data`) for the same reason, so this rename didn't orphan
the actual data.

| Service | URL |
|---|---|
| RA Web (enrollment) | https://localhost:8443/ejbca/ra/ |
| Admin Web | https://localhost:8443/ejbca/adminweb/ |
| Plain HTTP | http://localhost:8090 |

Whatever you set in `.env` is a local/dev credential for your own
machine — still don't reuse it, and don't carry it into Phase 4's GCP VM
as-is. Rotate before this ever runs anywhere with a public IP, and lock
down the admin UI per "Restricting admin access" below.

## Done: all three levels, server + client, issued and wired in

`ML-DSA-44-CA`, `ML-DSA-65-CA`, and `ML-DSA-87-CA` each exist as a
self-signed root CA (`ca init --tokenType soft`, no separate
`cryptotoken create` step needed - `--tokenType soft` creates the crypto
token inline as part of `ca init` itself). Each CA has issued exactly two
certs, both landing in `certs/ml-dsa-<level>/`:

- `pqc-poc-server-<level>` (`--certprofile SERVER`, `CN=pqc.poc.localhost`)
  → `server.pem`
- `pqc-poc-client-<level>` (`--certprofile ENDUSER`,
  `CN=pqc-poc-client-<level>`) → `client.pem`

The shape of the flow per level, using `ejbca.sh` via `docker exec ejbca
/opt/keyfactor/bin/ejbca.sh ...`:

1. `ca init --caname <name> --dn <dn> --keyspec ML-DSA-<level> --keytype
   ML-DSA-<level> -v 3650 --policy null -s ML-DSA-<level> --tokenType soft
   --tokenPass <pin>` - creates the CA and its crypto token together. The
   token PIN only matters again if the token ever needs reactivating
   (rare) - not needed for routine issuance once the CA is initialized.
   `ManagementCA` already exists out of the box in the container image, so
   `-superadmincn` wasn't needed for these (admin auth was already
   bootstrapped).
2. `ca getcacert --caname <name> -f <file>` - export the CA cert; this
   becomes `ca-chain.pem`.
3. On the client side (needs OpenSSL 3.5+, same constraint as the rest of
   this repo): `openssl genpkey -algorithm ML-DSA-<level>` +
   `openssl req -new` to generate a keypair and CSR.
4. `ra addendentity --username <user> --dn <dn> --caname <name> --type 1
   --token PEM --certprofile SERVER|ENDUSER --password <pw>`, then
   `createcert --username <user> --password <pw> -c <csr> -f <out>` to
   issue the cert.
5. `openssl verify -CAfile <ca file> <issued cert>` → `OK`.

### Gotchas found doing this for real (not just the spike)

- **`--altname "dNSName=..."` on `ra addendentity` didn't produce a SAN**
  in the issued cert, even though the command accepted it without error.
  The `SERVER` certificate profile likely needs its allowed-SAN-types
  configured explicitly (profile edit, not attempted) for this to take.
  Net effect: `server.pem` still has no SAN - see each
  `servers/<lang>/README.md` for how the clients work around that.
- **The end-entity delete command is `ra delendentity`, not
  `deleteendentity`** - the latter silently falls through to the CLI's
  top-level help text instead of erroring, which reads like nothing
  happened rather than "wrong command name."
- **`ra delendentity` needs the entity revoked first**, and then still
  prompts `Have you revoked the end entity [y/N]?` interactively -
  pipe `y` in (`echo y | docker exec -i ejbca ...`) when scripting it, or
  it silently aborts.
- If you're on Windows with Git Bash, path-like arguments (`/tmp/...`)
  can get silently rewritten to a Windows path by MSYS for most `docker`
  subcommands; export `MSYS_NO_PATHCONV=1` first. The one exception:
  `docker cp`'s *source* argument is a real host path and needs the
  normal MSYS rewrite to happen - don't set `MSYS_NO_PATHCONV=1` for that
  one, or it'll fail to find the file.

## Restricting admin access

Out of the box, anyone can reach the Admin Web UI. Before this runs
anywhere reachable beyond localhost (i.e. before Phase 4/GCP):

1. RA Web → Make New Request → template `ENDUSER`, choose your own CN
   for the admin identity, generate an RSA 2048 key by the CA, download
   the resulting PKCS#12.
2. Admin Web → Roles and Access Rules → remove the **Public Access
   Role** entirely.
3. Configure the **Super Administrator Role** to match `X509:CN =
   <your admin CN>` against the Management CA, and delete the
   `PublicAccessAuthenticationToken` member — from then on, only someone
   holding that admin client cert can manage the instance.

(This is Keyfactor's own documented hardening step, not something specific
to this project — see the official Docker tutorial linked above for the
click-by-click version if the RA Web flow above needs more detail.)

## Known limitation carried forward

Per [Keyfactor's PQC keys/signatures reference](https://docs.keyfactor.com/ejbca/latest/post-quantum-cryptography-keys-and-signatures),
CRLs can be generated for ML-DSA CAs, but OCSP and some other protocols
are still noted as in development for PQC algorithms — relevant to the
"Lifecycle (issuance, renewal, revocation)" goal in the repo root
README; CRL-based revocation should work, OCSP-based revocation may not
yet, worth re-checking against whatever EJBCA version is actually pulled
at Phase 2/4 time (`docker-compose.ejbca.yml` tracks `:latest`).
