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

    src_files = [Path('out/results.json'), Path('out/merkle_matches.json'), Path('out/merkle_proofs.json')]
    urls: Set[str] = set()
    for p in src_files:
        j = load_json(p)
        urls.update(find_urls_in_obj(j))

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
