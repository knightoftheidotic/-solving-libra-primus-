#!/usr/bin/env bash
set -euo pipefail

# Safe Hashcat attack wrapper.
# Runs hashcat locally with a bounded runtime and captures cracked candidates to feed into the local solver.
# This wrapper will NOT perform any network actions.
#
# Usage:
#   ./tools/run_hashcat_attack.sh -m <hash-type> -a <attack-mode> -o outdir --runtime 300 --hash-file inputs/hashes.txt [--wordlist inputs/wordlist.txt]
#
# By default this runs a dictionary+rules style attack using inputs/wordlist.txt and tools/best64.rule

HASHCAT=$(command -v hashcat || true)
if [ -z "$HASHCAT" ]; then
  echo "hashcat not found in PATH. Install hashcat to run attacks." >&2
  exit 2
fi

# Defaults
HASH_FILE="inputs/hashes.txt"
WORDLIST="inputs/wordlist.txt"
RULES="tools/best64.rule"
RUNTIME=300
OUT_DIR="out"
HASH_TYPE=0
ATTACK_MODE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--hash-type) HASH_TYPE="$2"; shift 2;;
    -a|--attack-mode) ATTACK_MODE="$2"; shift 2;;
    --hash-file) HASH_FILE="$2"; shift 2;;
    --wordlist) WORDLIST="$2"; shift 2;;
    --rules) RULES="$2"; shift 2;;
    --runtime) RUNTIME="$2"; shift 2;;
    -o|--out) OUT_DIR="$2"; shift 2;;
    -h|--help) echo "Usage: $0 [-m hash-type] [--runtime seconds] [--hash-file path] [--wordlist path]"; exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

mkdir -p "$OUT_DIR"

POTFILE="$OUT_DIR/hashcat_attack.potfile"
CAND_FILE="$OUT_DIR/hashcat_attack_candidates.txt"

echo "Running hashcat (safe wrapper)"
echo "  hashcat: $HASHCAT"
echo "  hash-type: $HASH_TYPE, attack-mode: $ATTACK_MODE, runtime: ${RUNTIME}s"
echo "  hash-file: $HASH_FILE"

# Run hashcat with a bounded runtime. We use --potfile-path to separate results.
# Use --runtime to stop after given seconds.

# If attack mode is 0 (dictionary), run with provided wordlist and rules if available.
if [ "$ATTACK_MODE" -eq 0 ]; then
  if [ -f "$RULES" ]; then
    $HASHCAT -m "$HASH_TYPE" -a 0 "$HASH_FILE" "$WORDLIST" -r "$RULES" --potfile-path "$POTFILE" --runtime "$RUNTIME"
  else
    $HASHCAT -m "$HASH_TYPE" -a 0 "$HASH_FILE" "$WORDLIST" --potfile-path "$POTFILE" --runtime "$RUNTIME"
  fi
else
  # For other modes, invoke hashcat with minimal risk and runtime bound; user may extend this command.
  $HASHCAT -m "$HASH_TYPE" -a "$ATTACK_MODE" "$HASH_FILE" "$WORDLIST" --potfile-path "$POTFILE" --runtime "$RUNTIME"
fi

echo "Hashcat run complete. Extracting cracked candidates from potfile..."

if [ -f "$POTFILE" ]; then
  # Hashcat potfile entries are in format: <hash>:<plaintext>
  cut -d ':' -f2- "$POTFILE" | sed '/^$/d' | awk '!seen[$0]++' > "$CAND_FILE"
  echo "Wrote $(wc -l < "$CAND_FILE") unique candidate(s) to $CAND_FILE"
  # Copy into inputs and run local solver
  cp "$CAND_FILE" inputs/hashcat_candidates.txt
  echo "Running local solver on generated candidates..."
  python3 run_hash_solver.py --merkle
  echo "Solver finished. Results: out/results.json, out/merkle_matches.json"
else
  echo "No potfile produced; no candidates to test."
fi

echo "Done."
