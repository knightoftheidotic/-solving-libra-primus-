#!/usr/bin/env bash
# Small helper to send a test webhook to a local webhook_receiver instance.
# Requires: curl, python3 (for signature helper)

set -euo pipefail

PORT=${1:-9000}
URL="http://localhost:${PORT}/webhook"
SECRET=${WEBHOOK_SECRET:-test-secret}
PAYLOAD_FILE=${2:-tools/test_payload.json}

if [ ! -f "$PAYLOAD_FILE" ]; then
  echo "Creating sample payload at $PAYLOAD_FILE"
  cat > "$PAYLOAD_FILE" <<'JSON'
{"test": "webhook", "ts": 0}
JSON
fi

SIG=$(python3 tools/sign_webhook.py --secret "$SECRET" --file "$PAYLOAD_FILE")

curl -v -X POST "$URL" -H "Content-Type: application/json" -H "X-Signature: $SIG" --data-binary "@$PAYLOAD_FILE"
