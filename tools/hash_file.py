#!/usr/bin/env python3
"""Compute hashes for a file and write a log.

Usage:
  python3 tools/hash_file.py /path/to/candidate10.txt

Writes a log next to the file named <file>_hash_log.txt containing SHA1, SHA256, SHA512.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from datetime import datetime


def hash_file(path: Path) -> dict:
    algos = {
        'SHA1': hashlib.sha1(),
        'SHA256': hashlib.sha256(),
        'SHA512': hashlib.sha512(),
    }
    with path.open('rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            for h in algos.values():
                h.update(chunk)
    return {name: h.hexdigest() for name, h in algos.items()}


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 tools/hash_file.py /path/to/file')
        raise SystemExit(2)
    p = Path(sys.argv[1])
    if not p.exists():
        print('File not found:', p)
        raise SystemExit(2)

    results = hash_file(p)
    logp = p.with_name(p.stem + '_hash_log.txt')
    with logp.open('w', encoding='utf-8') as f:
        f.write(f'File: {p}\n')
        f.write(f'Timestamp: {datetime.utcnow().isoformat()}Z\n')
        for name, val in results.items():
            f.write(f'{name}: {val}\n')

    print(f'Hashing {p.name} complete. Results saved in {logp}')
    for name, val in results.items():
        print(f'{name}: {val}')


if __name__ == '__main__':
    main()
