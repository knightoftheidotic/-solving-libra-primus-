#!/usr/bin/env python3
"""Local wordlist-based hash verifier (safe, no network actions).

This script implements a small, safe solver for verifying hashes against a
local wordlist. It is intentionally local-only and will not perform any
network activity (even if `USE_TOR` is set). If you want to test Tor usage,
run it on a self-hosted runner that you control and ensure legal compliance.

Input files (relative to repo root):
 - `inputs/hashes.txt`  : newline-separated hex hashes (SHA256)
 - `inputs/wordlist.txt`: newline-separated candidate plaintexts

Output:
 - `out/results.json` : JSON mapping hash -> discovered plaintext or null

This is designed to be safe and auditable. Replace or extend with your real
solver logic, but avoid network calls unless you have authorization.
"""
import hashlib
import json
import os
import sys
from pathlib import Path


def compute_sha256(s: bytes) -> str:
    return hashlib.sha256(s).hexdigest()


def load_lines(path: Path):
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]


def solver_main():
    repo_root = Path(os.environ.get("WORKING_DIR", os.getcwd()))
    print(f"Repo root / working dir: {repo_root}")

    inputs_dir = repo_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    hashes_path = inputs_dir / "hashes.txt"
    wordlist_path = inputs_dir / "wordlist.txt"

    hashes = load_lines(hashes_path)
    wordlist = load_lines(wordlist_path)

    print(f"Loaded {len(hashes)} target hash(es) and {len(wordlist)} candidate(s)")

    out_dir = repo_root / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"

    # Create mapping of candidate hash -> plaintext for quick lookup
    candidate_map = {compute_sha256(w.encode("utf-8")): w for w in wordlist}

    results = {}
    for h in hashes:
        h_clean = h.strip().lower()
        if not h_clean:
            continue
        found = candidate_map.get(h_clean)
        results[h_clean] = found

    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote results to {results_path}")
    return 0


def main():
    use_tor = os.environ.get("USE_TOR", "0").strip()
    if use_tor == "1":
        # Safety: only allow Tor mode on self-hosted runners under explicit control.
        print("USE_TOR=1 detected. This script will NOT perform network actions.")
        print("If you intend to route traffic through Tor, run this on a self-hosted runner and supervise Tor there.")

    return solver_main()


if __name__ == "__main__":
    try:
        rc = main()
        sys.exit(rc)
    except Exception as e:
        print("Error running solver:", e)
        sys.exit(2)
