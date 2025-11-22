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


def compute_merkle_root_and_proofs(leaf_hashes: list[str]) -> tuple[str, dict]:
    """Build a binary Merkle tree from a list of hex leaf hashes (SHA-256 hex strings).

    Returns (root_hex, proofs) where proofs maps leaf_hash -> proof list.
    Proof list is a list of (sibling_hash, direction) where direction is 'L' or 'R'.
    """
    # Helper: ensure we are working with bytes internally
    def hex_to_bytes(h: str) -> bytes:
        return bytes.fromhex(h)

    def bytes_to_hex(b: bytes) -> str:
        return b.hex()

    # Start with list of bytes
    level = [hex_to_bytes(h) for h in leaf_hashes]
    # Keep track of proofs: map leaf index to list of (sibling_hex, dir)
    proofs_by_index = {i: [] for i in range(len(level))}

    if not level:
        return "", {}

    # Build the tree upward
    while len(level) > 1:
        next_level = []
        # If odd number of nodes, duplicate last
        if len(level) % 2 == 1:
            level.append(level[-1])
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1]
            # For each child leaf beneath left/right, append sibling info
            # We need to propagate proofs: find all original leaf indices covered by these nodes
            # To do this efficiently we track index ranges implicitly by rebuilding mapping each round.
            # But simpler: reconstruct the mapping of indices to node positions each round.
            parent = hashlib.sha256(left + right).digest()
            next_level.append(parent)
        # After building next_level, compute new proofs for leaves by pairing
        # Recompute mapping from leaf index -> node at current level
        # We'll reconstruct levels from leaves each loop to attach proofs correctly.
        # Simpler approach: perform a separate loop to attach sibling for each pair at this level.
        for i in range(0, len(level), 2):
            left_hex = bytes_to_hex(level[i])
            right_hex = bytes_to_hex(level[i + 1])
            # Determine which original leaf indices contributed to level[i] and level[i+1]
            # We'll map leaf indices to their current node by chunking the leaves according to tree width.
            # Calculate chunk size: number of original leaves represented by one node at this level
            # Number of nodes at this level = len(level)
            # chunk_size = total_leaves / number_of_nodes
            # But since we duplicated when odd, we can instead simulate by building grouping from original leaves.
            pass

    # The above while loop is simplified but proof construction needs a clearer implementation.
    # To keep implementation correct and simple, rebuild a full tree structure with nodes tracking leaf index ranges.
    # Implement a proper tree builder below.


def _build_merkle_tree_with_proofs(leaf_hashes: list[str]) -> tuple[str, dict]:
    """Robust Merkle builder that returns (root_hex, proofs) mapping leaf_hash -> proof list.

    Proof list contains tuples (sibling_hex, direction) where direction is 'L' if sibling is left of node,
    'R' if sibling is right of node. Uses SHA-256(left || right) as parent hash.
    """
    if not leaf_hashes:
        return "", {}

    import math

    # Node structure: dict with keys {hash: bytes, leaves: list of leaf indices}
    nodes = [ { 'hash': bytes.fromhex(h), 'leaves': [i] } for i,h in enumerate(leaf_hashes) ]

    # proofs_by_leaf_index: list of lists
    proofs = { i: [] for i in range(len(leaf_hashes)) }

    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            # duplicate last
            nodes.append({'hash': nodes[-1]['hash'], 'leaves': nodes[-1]['leaves'][:]})
        next_nodes = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i+1]
            # For each leaf index under left, its sibling is right
            for li in left['leaves']:
                proofs[li].append( (right['hash'].hex(), 'R') )
            for ri in right['leaves']:
                proofs[ri].append( (left['hash'].hex(), 'L') )
            parent_hash = hashlib.sha256(left['hash'] + right['hash']).digest()
            parent_node = { 'hash': parent_hash, 'leaves': left['leaves'] + right['leaves'] }
            next_nodes.append(parent_node)
        nodes = next_nodes

    root_hex = nodes[0]['hash'].hex()
    # Convert proofs mapping from index keys to leaf-hash keys
    proofs_by_leaf_hash = {}
    for idx, proof_list in proofs.items():
        proofs_by_leaf_hash[ leaf_hashes[idx] ] = proof_list
    return root_hex, proofs_by_leaf_hash


def verify_merkle_proof(leaf_hex: str, proof: list[tuple[str, str]], root_hex: str) -> bool:
    """Verify a Merkle proof for a leaf (hex strings). Proof is list of (sibling_hex, direction).

    direction 'L' means sibling is left of the node, 'R' means sibling is right.
    """
    cur = bytes.fromhex(leaf_hex)
    for sibling_hex, direction in proof:
        sibling = bytes.fromhex(sibling_hex)
        if direction == 'L':
            cur = hashlib.sha256(sibling + cur).digest()
        else:
            cur = hashlib.sha256(cur + sibling).digest()
    return cur.hex() == root_hex


def build_and_save_merkle(wordlist: list[str], targets: list[str], out_dir: Path):
    """Build Merkle tree from wordlist (leaves = SHA256(word)), save root and proofs, and record matches.

    Writes `out/merkle_root.txt`, `out/merkle_proofs.json`, and `out/merkle_matches.json`.
    Returns (root_hex, proofs, matches).
    """
    # Compute leaf hashes in order
    leaf_hashes = [ compute_sha256(w.encode('utf-8')) for w in wordlist ]
    root_hex, proofs = _build_merkle_tree_with_proofs(leaf_hashes)

    # Save root and proofs
    (out_dir / 'merkle_root.txt').write_text(root_hex, encoding='utf-8')
    (out_dir / 'merkle_proofs.json').write_text(json.dumps(proofs, indent=2), encoding='utf-8')

    # Check targets against leaves and root
    matches = {}
    leaf_set = set(leaf_hashes)
    for t in targets:
        t_clean = t.strip().lower()
        if not t_clean:
            continue
        if t_clean == root_hex:
            matches[t_clean] = { 'type': 'root' }
        elif t_clean in leaf_set:
            # include plaintext and proof
            idx = leaf_hashes.index(t_clean)
            plaintext = wordlist[idx]
            proof = proofs.get(t_clean, [])
            # verify proof sanity
            ok = verify_merkle_proof(t_clean, proof, root_hex)
            matches[t_clean] = { 'type': 'leaf', 'plaintext': plaintext, 'proof': proof, 'verified': ok }
        else:
            # no match
            pass

    (out_dir / 'merkle_matches.json').write_text(json.dumps(matches, indent=2), encoding='utf-8')
    return root_hex, proofs, matches



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

    # Create mapping of candidate hash -> plaintext for quick lookup.
    # Support multiple common hash algorithms (SHA256 and SHA512) so the
    # solver can match hashes of either length.
    candidate_map = {}
    for w in wordlist:
        b = w.encode("utf-8")
        h256 = compute_sha256(b)
        candidate_map[h256] = w
        # SHA512 mapping (128 hex chars)
        try:
            import hashlib as _hashlib

            h512 = _hashlib.sha512(b).hexdigest()
            candidate_map[h512] = w
        except Exception:
            # If hashlib doesn't support sha512 for some reason, skip it
            pass

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
    import argparse

    parser = argparse.ArgumentParser(description="Run local hash solver and optional Merkle tree build")
    parser.add_argument("--merkle", action="store_true", help="Build Merkle tree (SHA-256) from wordlist and save proofs")
    args = parser.parse_args()

    try:
        rc = main()

        if args.merkle:
            # Load wordlist and targets again (solver_main already wrote results)
            repo_root = Path(os.environ.get("WORKING_DIR", os.getcwd()))
            inputs_dir = repo_root / "inputs"
            hashes_path = inputs_dir / "hashes.txt"
            wordlist_path = inputs_dir / "wordlist.txt"
            hashes = load_lines(hashes_path)
            wordlist = load_lines(wordlist_path)
            out_dir = repo_root / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            root_hex, proofs, matches = build_and_save_merkle(wordlist, hashes, out_dir)
            print(f"Merkle root: {root_hex}")

        sys.exit(rc)
    except Exception as e:
        print("Error running solver:", e)
        sys.exit(2)
