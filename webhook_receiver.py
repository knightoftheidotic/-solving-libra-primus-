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
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# Toggle verbose debug printing. Set in __main__ via --verbose flag or WEBHOOK_VERBOSE env var.
VERBOSE = False
DEBUG_LOG_PATH = os.path.join(os.getcwd(), "out", "webhook_debug.log")


def debug_log(msg: str):
    """Write a timestamped debug message to both stdout (when VERBOSE) and to the debug log file."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    line = f"[{ts}] {msg}\n"
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass
    if VERBOSE:
        try:
            print(line, end="")
        except Exception:
            pass


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

        if VERBOSE:
            try:
                debug_log("Received payload (first 1024 bytes): " + repr(body[:1024]))
            except Exception:
                pass

        # Try to parse JSON payload and extract SHA256-like hashes (safe local operation).
        try:
            import json
            from tools.parse_hashes import extract_hashes_from_text

            text = None
            try:
                obj = json.loads(body.decode("utf-8", errors="ignore"))
                # Look for common fields that may contain the message content
                if isinstance(obj, dict):
                    # Check several candidate fields
                    for field in ("content", "message", "text", "body", "payload"):
                        if field in obj and isinstance(obj[field], str):
                            text = obj[field]
                            break
                    # Otherwise, stringify the full object
                    if text is None:
                        text = json.dumps(obj)
                else:
                    text = str(obj)
            except Exception:
                # Not JSON or parse failed — fall back to raw body text
                text = body.decode("utf-8", errors="ignore")

            hashes = extract_hashes_from_text(text)
            if VERBOSE:
                debug_log("Extracted text for parsing (first 1024 chars): " + (text or "")[:1024])
                debug_log("Found hashes: " + str(hashes))
            if hashes:
                inputs_dir = os.path.join(os.getcwd(), "inputs")
                os.makedirs(inputs_dir, exist_ok=True)
                hashes_file = os.path.join(inputs_dir, "hashes.txt")
                # Read existing hashes and append any new unique ones
                existing = set()
                if os.path.exists(hashes_file):
                    with open(hashes_file, "r", encoding="utf-8", errors="ignore") as fh:
                        for ln in fh:
                            ln = ln.strip().lower()
                            if ln:
                                existing.add(ln)
                appended = []
                with open(hashes_file, "a", encoding="utf-8") as fh:
                    for h in hashes:
                        if h not in existing:
                            fh.write(h + "\n")
                            appended.append(h)
                if appended:
                    debug_log(f"Appended {len(appended)} new hash(es) to {hashes_file}: {appended}")
        # Also attempt to extract URLs (including www.*) for debugging and capture
        try:
            from tools.parse_urls import extract_urls_from_text

            urls = extract_urls_from_text(text if text is not None else body.decode("utf-8", errors="ignore"))
            if urls:
                urls_path = os.path.join(os.getcwd(), "out", "urls.txt")
                existing_urls = set()
                if os.path.exists(urls_path):
                    with open(urls_path, "r", encoding="utf-8", errors="ignore") as uf:
                        for ln in uf:
                            existing_urls.add(ln.strip())
                appended_urls = []
                with open(urls_path, "a", encoding="utf-8") as uf:
                    for u in urls:
                        if u not in existing_urls:
                            uf.write(u + "\n")
                            appended_urls.append(u)
                if appended_urls:
                    debug_log(f"Appended {len(appended_urls)} URL(s) to {urls_path}: {appended_urls}")
        except Exception as e:
            debug_log(f"URL extraction failed: {e}")
        except Exception as e:
            print("Hash extraction failed:", e)

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
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug output and write debug log to out/webhook_debug.log")
    args = parser.parse_args()

    # Enable VERBOSE if requested on the command line or via WEBHOOK_VERBOSE env var
    global VERBOSE
    VERBOSE = args.verbose or os.environ.get("WEBHOOK_VERBOSE", "0").strip() == "1"
    # Ensure out directory exists so debug log can be created
    os.makedirs("out", exist_ok=True)
    if VERBOSE:
        debug_log("Verbose logging enabled")

    run_server(args.port)
