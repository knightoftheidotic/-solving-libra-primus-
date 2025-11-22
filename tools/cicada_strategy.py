#!/usr/bin/env python3
"""Cicada-3301 style heuristic strategy generator.

Generates candidate plaintexts using puzzle-style heuristics:
- concatenation of tokens (limited)
- rot13, base64 encode/decode, hex encode/decode
- common prefixes/suffixes and separators
All candidates are tested against target hashes (SHA-256 and SHA-512).

Safeguards:
- limit number of tokens used for concatenation (MAX_TOKENS)
- stop after MAX_CANDIDATES tested

Writes results to `out/results_cicada.json` and prints progress.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from itertools import product
from pathlib import Path
from typing import Iterable, List


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha512_hex(b: bytes) -> str:
    return hashlib.sha512(b).hexdigest()


def load_lines(p: Path) -> List[str]:
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text(encoding='utf-8', errors='ignore').splitlines() if ln.strip() and not ln.strip().startswith('#')]


def codecs_rot13(s: str) -> str:
    def rot(ch):
        o = ord(ch)
        if 65 <= o <= 90:
            return chr((o - 65 + 13) % 26 + 65)
        if 97 <= o <= 122:
            return chr((o - 97 + 13) % 26 + 97)
        return ch
    return ''.join(rot(c) for c in s)


def try_base64_decode(s: str) -> str | None:
    try:
        padded = s + '=' * (-len(s) % 4)
        decoded = base64.b64decode(padded, validate=True)
        return decoded.decode('utf-8', errors='strict')
    except Exception:
        return None


def try_hex_decode(s: str) -> str | None:
    try:
        decoded = bytes.fromhex(s)
        return decoded.decode('utf-8', errors='strict')
    except Exception:
        return None


COMMON_PREFIXES = ['', 'the', 'cicada', '3301', 'ccida', 'ccida3301', 'cipher']
COMMON_SUFFIXES = ['', '3301', '!', '.com', '.onion', '-3301']
SEPARATORS = ['', '_', '-', '.', '/', '']


def generate_candidates(tokens: List[str], max_tokens: int = 100, max_candidates: int = 200000) -> Iterable[str]:
    seen = set()
    count = 0

    def yield_cand(c: str):
        nonlocal count
        if not c:
            return
        if c in seen:
            return
        seen.add(c)
        count += 1
        yield c

    tokens_limited = tokens[:max_tokens]

    # single-token transforms
    for t in tokens_limited:
        for p in COMMON_PREFIXES:
            for sfx in COMMON_SUFFIXES:
                cand = f"{p}{t}{sfx}"
                for v in yield_cand(cand):
                    yield v
                for v in yield_cand(cand.lower()):
                    yield v
                for v in yield_cand(cand.upper()):
                    yield v
                for v in yield_cand(cand.title()):
                    yield v
                r = codecs_rot13(cand)
                for v in yield_cand(r):
                    yield v
                try:
                    b64 = base64.b64encode(cand.encode('utf-8')).decode('ascii')
                    for v in yield_cand(b64):
                        yield v
                except Exception:
                    pass
                dec = try_base64_decode(t)
                if dec:
                    for v in yield_cand(dec):
                        yield v
                hdec = try_hex_decode(t)
                if hdec:
                    for v in yield_cand(hdec):
                        yield v

        if count >= max_candidates:
            return

    # pairwise concatenations (bounded)
    for a, b in product(tokens_limited, tokens_limited):
        for sep in SEPARATORS:
            cand = f"{a}{sep}{b}"
            for v in yield_cand(cand):
                yield v
            for pre in COMMON_PREFIXES:
                for suf in COMMON_SUFFIXES:
                    cand2 = f"{pre}{cand}{suf}"
                    for v in yield_cand(cand2):
                        yield v
            try:
                b64 = base64.b64encode(cand.encode('utf-8')).decode('ascii')
                for v in yield_cand(b64):
                    yield v
            except Exception:
                pass

        if count >= max_candidates:
            return


def main():
    repo = Path('.')
    inputs = repo / 'inputs'
    out = repo / 'out'
    out.mkdir(parents=True, exist_ok=True)

    tokens = load_lines(inputs / 'wordlist.txt')
    targets = [h.strip().lower() for h in load_lines(inputs / 'hashes.txt')]
    targets_set = set(targets)
    if not tokens:
        print('No tokens found in inputs/wordlist.txt; aborting')
        return
    if not targets:
        print('No target hashes found in inputs/hashes.txt; aborting')
        return

    MAX_TOKENS = 200
    MAX_CANDIDATES = 200000
    start = time.time()
    tested = 0
    found = {}

    print(f'Running Cicada strategy: up to {MAX_CANDIDATES} candidates using first {MAX_TOKENS} tokens')
    for cand in generate_candidates(tokens, max_tokens=MAX_TOKENS, max_candidates=MAX_CANDIDATES):
        tested += 1
        b = cand.encode('utf-8')
        h256 = sha256_hex(b)
        if h256 in targets_set and h256 not in found:
            found[h256] = cand
            print(f'FOUND SHA256: {h256} -> {cand}')
        h512 = sha512_hex(b)
        if h512 in targets_set and h512 not in found:
            found[h512] = cand
            print(f'FOUND SHA512: {h512} -> {cand}')
        if set(found.keys()) >= targets_set:
            break
        if tested % 5000 == 0:
            elapsed = time.time() - start
            print(f'Tested {tested} candidates ({elapsed:.1f}s elapsed)')

    outp = out / 'results_cicada.json'
    outp.write_text(json.dumps(found, indent=2), encoding='utf-8')
    elapsed = time.time() - start
    print(f'Done. Tested {tested} candidates in {elapsed:.1f}s. Found {len(found)} matches. Results: {outp}')


if __name__ == '__main__':
    main()
