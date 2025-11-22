#!/usr/bin/env python3
"""Utility to compute HMAC-SHA256 signature for webhook payloads.

Usage:
  python3 tools/sign_webhook.py --secret SECRET --file payload.json
  python3 tools/sign_webhook.py --secret SECRET --data '{"x":1}'

Outputs the hexdigest signature that should be placed in the `X-Signature` header.
"""
import argparse
import hmac
import hashlib
import sys


def compute_hmac(secret: str, data: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--secret", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="File path to read payload from")
    g.add_argument("--data", help="Raw string payload")
    args = p.parse_args()

    if args.file:
        data = open(args.file, "rb").read()
    else:
        data = args.data.encode("utf-8")

    print(compute_hmac(args.secret, data))


if __name__ == "__main__":
    main()
