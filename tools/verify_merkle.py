#!/usr/bin/env python3
"""Simple Merkle proof verifier CLI.

Usage examples:
  # Verify a proof from the solver's match file
  python3 tools/verify_merkle.py --match-key 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

  # Verify by providing root, leaf (hex), and proof JSON file
  python3 tools/verify_merkle.py --root-file out/merkle_root.txt --leaf-hash <hex> --proof-file out/merkle_proofs.json

This script accepts either plaintext (via --leaf-data) or the leaf hash (via --leaf-hash).
If you pass --match-key it will read `out/merkle_matches.json` and verify that entry against `out/merkle_root.txt`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import List, Tuple, Optional


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_root_from_proof(leaf_hash: str, proof: List[Tuple[str, str]]) -> str:
    """Compute merkle root given leaf hash and proof.

    proof is a list of [sibling_hash, position] where position is 'L' if sibling is left,
    or 'R' if sibling is right.
    """
    cur = bytes.fromhex(leaf_hash)
    for item in proof:
        sibling, pos = item
        sib = bytes.fromhex(sibling)
        if pos.upper() == 'L':
            cur = hashlib.sha256(sib + cur).digest()
        else:
            cur = hashlib.sha256(cur + sib).digest()
    return cur.hex()


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def main():
    p = argparse.ArgumentParser(description='Verify a Merkle proof produced by the solver')
    p.add_argument('--root-file', type=Path, default=Path('out/merkle_root.txt'))
    p.add_argument('--proof-file', type=Path, default=Path('out/merkle_proofs.json'))
    p.add_argument('--matches-file', type=Path, default=Path('out/merkle_matches.json'))
    p.add_argument('--leaf-hash', help='Leaf hash (hex)')
    p.add_argument('--leaf-data', help='Leaf plaintext data (will be sha256-ed)')
    p.add_argument('--match-key', help='Key to look up in matches file (leaf hash hex)')
    args = p.parse_args()

    root = args.root_file.read_text().strip()
    proof_db = load_json(args.proof_file) if args.proof_file.exists() else {}
    matches = load_json(args.matches_file) if args.matches_file.exists() else {}

    leaf_hash = None
    proof = None

    if args.match_key:
        key = args.match_key
        entry = matches.get(key)
        if not entry:
            print(f"No match entry for key: {key}")
            raise SystemExit(2)
        if 'proof' not in entry:
            print(f"Match for {key} has no proof field.")
            raise SystemExit(2)
        proof = entry['proof']
        leaf_hash = key

    else:
        if args.leaf_data:
            leaf_hash = sha256_hex(args.leaf_data.encode('utf-8'))
        elif args.leaf_hash:
            leaf_hash = args.leaf_hash
        else:
            print('Either --match-key or --leaf-hash/--leaf-data must be provided')
            raise SystemExit(2)

        # If explicit proof-file contains a mapping, try to read proof by leaf-hash
        if proof_db and isinstance(proof_db, dict):
            proof = proof_db.get(leaf_hash)
            if proof is None:
                # maybe proofs are keyed by node id - warn
                print('No direct proof entry found in proof file for leaf; you can pass a proof manually by editing the file or use --match-key')

    if proof is None:
        print('No proof available for the provided leaf.')
        raise SystemExit(2)

    # Proof might be stored as list of [hash, pos] items
    computed = compute_root_from_proof(leaf_hash, proof)

    print(f'Provided root: {root}')
    print(f'Computed root: {computed}')
    if computed == root:
        print('OK: proof verifies against root')
        raise SystemExit(0)
    else:
        print('FAIL: proof does not match root')
        raise SystemExit(3)


if __name__ == '__main__':
    main()
