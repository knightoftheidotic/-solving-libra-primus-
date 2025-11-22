# Solving Libra Primus — Hash verifier (safe)

This repository contains a local, auditable SHA256 hash verifier and a
safe webhook receiver for testing. It is intentionally network-disabled by
default; optional network/Tor features are available but must be explicitly
enabled and run only on self-hosted machines you control.

Key files
- `run_hash_solver.py` — Local wordlist-based SHA256 verifier. No network by default.
- `webhook_receiver.py` — Minimal local webhook receiver with HMAC-SHA256 verification.
- `inputs/` — Example `hashes.txt` and `wordlist.txt` for local testing.
- `.github/workflows/run-solver.yml` — CI configuration. Network/Tor steps only run on self-hosted runners when explicitly enabled.

Safety & legal
- This project must not be used to access illegal or unauthorized content. Do not point the solver or webhook to content you do not own or do not have explicit permission to access.
- Tor/network features are gated behind environment flags and the workflow is set to only run Tor steps on self-hosted runners.
- If you plan to enable network access, ensure you have documented authorization and comply with laws and competition rules (e.g., CCIDA 3301 allowances).

Quick start (local)

1. Install requirements (recommended in a virtualenv):

```bash
python3 -m pip install -r requirements.txt
```

2. Run the local solver (no network):

```bash
python3 run_hash_solver.py
cat out/results.json
```

3. Run the local webhook receiver (for test webhooks):

```bash
export WEBHOOK_SECRET="your-secret"
python3 webhook_receiver.py --port 9000
```

If you want to enable network or Tor features, read `docs/TOR_HARDENING.md` and only enable them on self-hosted machines you control.
# -solving-libra-primus-
 I am working on the dots on one of the pages 
