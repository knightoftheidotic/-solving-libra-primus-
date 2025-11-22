#!/usr/bin/env python3
"""Utilities to extract URLs (http/https/www) from text.

Provides a small helper `extract_urls_from_text` which returns unique URLs
found in the input text. This is used by the webhook receiver for debugging
and to capture any `www.` entries referenced in payloads.
"""
import re
from typing import List

# Very small URL regex: matches http(s)://... or www.... up to whitespace
_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)


def extract_urls_from_text(text: str) -> List[str]:
    if not text:
        return []
    found = _URL_RE.findall(text)
    # normalize and deduplicate preserving order
    seen = set()
    out = []
    for u in found:
        # strip trailing punctuation and quotes
        u2 = u.rstrip("\"'.,;:()[]{}<>")
        if u2 not in seen:
            seen.add(u2)
            out.append(u2)
    return out


if __name__ == "__main__":
    import sys
    txt = sys.stdin.read() if not sys.argv[1:] else open(sys.argv[1]).read()
    for u in extract_urls_from_text(txt):
        print(u)
