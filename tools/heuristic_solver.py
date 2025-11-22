#!/usr/bin/env python3
"""Heuristic solver: generate candidate variants from `inputs/wordlist.txt` and test against `inputs/hashes.txt`.

Produces `out/results_heuristic.json` with any discovered matches and prints progress.

Transforms applied (configurable in-script):
- case variants (lower, upper, title)
- limited leetspeak substitutions (a->4, e->3, i->1, o->0, s->5, t->7) limited to up to 2 replacements
- common prefixes and suffixes appended/prepended

This stays local-only and does not perform network actions.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import itertools
from typing import Iterable, List, Set


def sha256_hex(s: bytes) -> str:
    return hashlib.sha256(s).hexdigest()


def sha512_hex(s: bytes) -> str:
    return hashlib.sha512(s).hexdigest()


def load_lines(p: Path) -> List[str]:
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text(encoding='utf-8', errors='ignore').splitlines() if ln.strip() and not ln.strip().startswith('#')]


LEET_MAP = {
    'a': '4',
    'e': '3',
    'i': '1',
    'o': '0',
    's': '5',
    't': '7',
}

PREFIXES = ['', 'the', 'my', 'www.', 'http://', 'https://']
SUFFIXES = ['', '!', '.', '123', '2025', '.com']


def case_variants(word: str) -> Set[str]:
    return {word, word.lower(), word.upper(), word.title()}


def leet_variants(word: str, max_replacements: int = 2) -> Set[str]:
    # Find positions eligible
    positions = [i for i,c in enumerate(word.lower()) if c in LEET_MAP]
    variants = set()
    variants.add(word)
    # Try up to max_replacements replacements (combinatorial but limited by max_replacements)
    for r in range(1, min(max_replacements, len(positions)) + 1):
        for combo in itertools.combinations(positions, r):
            lst = list(word)
            for i in combo:
                c = lst[i]
                lst[i] = LEET_MAP.get(c.lower(), c)
            variants.add(''.join(lst))
    return variants


def generate_variants(word: str) -> Iterable[str]:
    for case in case_variants(word):
        for leet in leet_variants(case):
            for pre in PREFIXES:
                for suf in SUFFIXES:
                    yield f"{pre}{leet}{suf}"


def main():
    repo = Path('.')
    inputs = repo / 'inputs'
    out = repo / 'out'
    out.mkdir(parents=True, exist_ok=True)

    hashes = load_lines(inputs / 'hashes.txt')
    wordlist = load_lines(inputs / 'wordlist.txt')

    target_set = set(h.lower() for h in hashes)
    print(f"Loaded {len(target_set)} target hash(es) and {len(wordlist)} base candidate(s)")

    found = {}
    tried = 0
    # Keep a small cache to avoid retesting same candidate
    seen = set()

    for w in wordlist:
        for var in generate_variants(w):
            if var in seen:
                continue
            seen.add(var)
            tried += 1
            b = var.encode('utf-8')
            h256 = sha256_hex(b)
            h512 = sha512_hex(b)
            if h256 in target_set and h256 not in found:
                found[h256] = var
                print(f"MATCH SHA256: {h256} -> {var}")
            if h512 in target_set and h512 not in found:
                found[h512] = var
                print(f"MATCH SHA512: {h512} -> {var}")
            # quick exit if all targets found
            if set(found.keys()) >= target_set:
                break
        if set(found.keys()) >= target_set:
            break

    outp = out / 'results_heuristic.json'
    outp.write_text(json.dumps(found, indent=2), encoding='utf-8')
    print(f"Tried {tried} candidates, found {len(found)} matches. Results written to {outp}")


if __name__ == '__main__':
    main()
