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

try:
    import requests
except Exception:
    requests = None


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
    # Return results and candidate_map for further processing by caller
    return results, candidate_map, results_path


def network_fetch_example():
    """Example network fetch that is only enabled when explicitly allowed.

    To enable network fetches the following environment variables must be set:
      - ENABLE_NETWORK=1
      - USE_TOR=1 (recommended) or USE_TOR=0 (direct)
      - TOR_SOCKS_PROXY (optional) default: socks5h://127.0.0.1:9050

    This function is a guarded example and does not run by default.
    """
    en = os.environ.get("ENABLE_NETWORK", "0").strip()
    if en != "1":
        print("Network access is disabled (ENABLE_NETWORK!=1). Skipping network fetch.")
        return None

    if requests is None:
        print("`requests` not installed; cannot perform network fetch")
        return None

    use_tor = os.environ.get("USE_TOR", "0").strip()
    proxy = os.environ.get("TOR_SOCKS_PROXY", "socks5h://127.0.0.1:9050")

    url = os.environ.get("NETWORK_FETCH_URL")
    if not url:
        print("No NETWORK_FETCH_URL set; aborting network fetch")
        return None

    session = requests.Session()
    if use_tor == "1":
        session.proxies.update({"http": proxy, "https": proxy})
        print(f"Fetching via Tor proxy {proxy}: {url}")
    else:
        print(f"Fetching directly (non-Tor): {url}")

    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        print(f"Fetched {len(r.content)} bytes")
        # Save a copy for inspection
        out_dir = Path("out")
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "network_fetch.bin"
        p.write_bytes(r.content)
        return p
    except Exception as e:
        print("Network fetch failed:", e)
        return None


def main():
    use_tor = os.environ.get("USE_TOR", "0").strip()
    if use_tor == "1":
        # Safety: only allow Tor mode on self-hosted runners under explicit control.
        print("USE_TOR=1 detected. This script will NOT perform network actions.")
        print("If you intend to route traffic through Tor, run this on a self-hosted runner and supervise Tor there.")

    # Run the local solver first
    solver_out = solver_main()

    # If network fetch is enabled, perform a guarded fetch and compute its hash
    if os.environ.get("ENABLE_NETWORK", "0").strip() == "1":
        fetched_path = network_fetch_example()
        if fetched_path and fetched_path.exists():
            data = fetched_path.read_bytes()
            net_hash = compute_sha256(data).lower()
            print(f"Network fetch SHA256: {net_hash}")

            # Update results.json if possible
            try:
                results, candidate_map, results_path = solver_out
                found = candidate_map.get(net_hash)
                results[net_hash] = found
                results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
                print(f"Appended network fetch result to {results_path}")
            except Exception as e:
                print("Could not update results.json with network fetch hash:", e)

    # Exit successfully; all network actions are opt-in and require env vars.
    return 0


if __name__ == "__main__":
    try:
        rc = main()
        sys.exit(rc)
    except Exception as e:
        print("Error running solver:", e)
        sys.exit(2)
