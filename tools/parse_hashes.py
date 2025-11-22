#!/usr/bin/env python3
"""Utilities to extract candidate hash strings from text or JSON webhook payloads.

This module provides a simple, safe extractor for hexadecimal strings that
look like SHA256 hashes (64 hex characters). It does not perform any
network activity — it's intended to be used by the webhook receiver to
pull hash candidates out of incoming payloads (for auditing and local
verification).
"""
import re
from typing import List

# Regex to match 64-hex-character strings (case-insensitive)
_SHA256_RE = re.compile(r"\b([A-Fa-f0-9]{64})\b")


def extract_hashes_from_text(text: str) -> List[str]:
    """Return a list of unique lowercase SHA256-like hex strings found in text."""
    if not text:
        return []
    found = _SHA256_RE.findall(text)
    # normalize to lowercase and deduplicate while preserving order
    seen = set()
    out = []
    for h in found:
        hl = h.lower()
        if hl not in seen:
            seen.add(hl)
            out.append(hl)
    return out


if __name__ == "__main__":
    import sys
    txt = sys.stdin.read() if not sys.argv[1:] else open(sys.argv[1]).read()
    for h in extract_hashes_from_text(txt):
        print(h)
