#!/usr/bin/env python3
"""Extract URLs from solver output files and produce clickable links.

Scans `out/results.json` and `out/merkle_matches.json` for any plaintext fields
or other text that contains URLs. Writes results to `out/urls.txt` (one URL per line)
and `out/urls.md` (Markdown links) for easy viewing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Set


URL_RE = re.compile(r"(https?://[\w\-\.\~:/?#\[\]@!$&'()*+,;=%]+|www\.[\w\-\.\~:/?#@!$&'()*+,;=%]+)", re.IGNORECASE)
# Bare domain pattern (e.g. example.com or sub.example.co.uk)
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63})\b", re.IGNORECASE)


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def find_urls_in_obj(obj) -> Set[str]:
    found: Set[str] = set()
    if isinstance(obj, dict):
        for v in obj.values():
            found.update(find_urls_in_obj(v))
    elif isinstance(obj, list):
        for item in obj:
            found.update(find_urls_in_obj(item))
    elif isinstance(obj, str):
        for m in URL_RE.findall(obj):
            # normalize: add scheme if starts with www.
            if m.lower().startswith('www.'):
                found.add('http://' + m)
            else:
                found.add(m)
    return found


def main():
    out_dir = Path('out')
    out_dir.mkdir(parents=True, exist_ok=True)

    src_files = [
        Path('out/results.json'),
        Path('out/merkle_matches.json'),
        Path('out/merkle_proofs.json'),
        Path('out/merkle_root.txt'),
        Path('inputs/wordlist.txt'),
        Path('inputs/hashes.txt'),
    ]
    urls: Set[str] = set()
    for p in src_files:
        if not p.exists():
            continue
        if p.suffix.lower() in ('.json',):
            j = load_json(p)
            urls.update(find_urls_in_obj(j))
        else:
            # treat as plain text
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            # find full URLs first
            for m in URL_RE.findall(text):
                if m.lower().startswith('www.'):
                    urls.add('http://' + m)
                else:
                    urls.add(m)
            # find bare domains, avoid matching those already captured
            for m in DOMAIN_RE.findall(text):
                if '.' in m:
                    # normalize to http://
                    candidate = m if m.lower().startswith('http') else 'http://' + m
                    urls.add(candidate)

    # Save plain list
    urls_txt = out_dir / 'urls.txt'
    urls_txt.write_text('\n'.join(sorted(urls)), encoding='utf-8')

    # Save markdown links
    urls_md = out_dir / 'urls.md'
    with urls_md.open('w', encoding='utf-8') as f:
        for u in sorted(urls):
            f.write(f'- [{u}]({u})\n')

    # Print summary
    if urls:
        print(f'Found {len(urls)} URL(s). Saved to: {urls_txt} and {urls_md}')
        for u in sorted(urls):
            print(u)
    else:
        print('No URLs found in outputs.')


if __name__ == '__main__':
    main()
