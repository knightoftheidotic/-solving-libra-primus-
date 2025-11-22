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

        # Process payload safely: write to out/ for auditing
        os.makedirs("out", exist_ok=True)
        payload_file = "out/webhook_payload.bin"
        with open(payload_file, "wb") as f:
            f.write(body)

        # Optionally trigger the solver on signed webhooks. This is gated by
        # environment variables to avoid accidental network activity.
        # Requirements to trigger:
        #   - PROCESS_WEBHOOK must be '1'
        #   - ENABLE_NETWORK must be '1' (network fetches are opt-in)
        #   - WEBHOOK_TRIGGER_CMD may specify a command to run (default runs run_hash_solver.py)
        process_webhook = os.environ.get("PROCESS_WEBHOOK", "0").strip()
        enable_network = os.environ.get("ENABLE_NETWORK", "0").strip()
        trigger_cmd = os.environ.get("WEBHOOK_TRIGGER_CMD", "python3 run_hash_solver.py")

        if process_webhook == "1":
            if enable_network != "1":
                print("PROCESS_WEBHOOK=1 set but ENABLE_NETWORK!=1; skipping network-enabled solver trigger")
            else:
                # Run the trigger command in a safe subprocess and capture output
                try:
                    import shlex
                    cmd = shlex.split(trigger_cmd)
                    # Provide environment to subprocess: inherit current env
                    env = os.environ.copy()
                    env["WORKING_DIR"] = os.getcwd()
                    print(f"Triggering solver via: {trigger_cmd}")
                    import subprocess
                    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
                    with open("out/webhook_solver_stdout.log", "wb") as so:
                        so.write(p.stdout or b"")
                    with open("out/webhook_solver_stderr.log", "wb") as se:
                        se.write(p.stderr or b"")
                    print(f"Solver trigger exited {p.returncode}")
                except Exception as e:
                    print("Failed to trigger solver:", e)

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
