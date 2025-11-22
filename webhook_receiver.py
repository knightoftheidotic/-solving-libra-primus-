#!/usr/bin/env python3
"""Minimal local webhook receiver with HMAC-SHA256 verification.

This small HTTP server listens on a configurable port (default 9000) and
accepts POST requests at `/webhook`. It validates an `X-Signature` header
which should be HMAC-SHA256 of the request body using a shared secret.

Security and legal notes:
 - This is intended for local testing only. Do NOT expose to the public
   internet without firewalling, TLS termination, authentication, and
   explicit authorization.
 - Keep the `WEBHOOK_SECRET` secure and rotate it as needed.
"""
import hmac
import hashlib
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        secret = os.environ.get("WEBHOOK_SECRET")
        if not secret:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Server misconfigured: WEBHOOK_SECRET not set")
            return

        sig_header = self.headers.get("X-Signature", "")
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected, sig_header):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Invalid signature")
            return

        # Process payload safely: here we just acknowledge and write to out/
        os.makedirs("out", exist_ok=True)
        with open("out/webhook_payload.bin", "wb") as f:
            f.write(body)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_server(port: int = 9000):
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    print(f"Listening for webhook POSTs on port {port}. Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", type=int, default=9000)
    args = parser.parse_args()

    run_server(args.port)
