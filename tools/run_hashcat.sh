#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run Hashcat (if installed) in a safe, local-only way to generate candidate plaintexts
# and feed them to the local solver. This script does NOT attempt any network access.
#
# Usage examples:
#   ./tools/run_hashcat.sh -m 0 -a 0 -w inputs/wordlist.txt --rules-file tools/best64.rule
#   ./tools/run_hashcat.sh --stdout -r tools/best64.rule -o out/hashcat_candidates.txt

HASHCAT=$(command -v hashcat || true)
if [ -z "$HASHCAT" ]; then
  echo "hashcat not found in PATH. Install hashcat locally to use this script: https://hashcat.net/hashcat/" >&2
  exit 2
fi

OUT_DIR="out"
mkdir -p "$OUT_DIR"

show_help() {
  cat <<'EOF'
Usage: run_hashcat.sh [hashcat args...] --target-hash <hex> [--hash-type <num>] [--top-output <file>]

This wrapper runs hashcat in a safe way to produce candidate plaintexts and then checks
them locally against the target hashes using our solver. By default it expects you will
either run hashcat in --stdout mode to generate candidates, or point it to a wordlist.

Examples:
  # Generate candidates from wordlist + rules and save to file
  ./tools/run_hashcat.sh --stdout -a 0 -r tools/best64.rule inputs/wordlist.txt > out/hashcat_candidates.txt

  # Use hashcat to try to crack a single hash (hashcat attack) and then export candidates
  ./tools/run_hashcat.sh -m 0 -a 3 -w 3  # see hashcat docs for modes

EOF
}

if [ "$#" -eq 0 ]; then
  show_help
  exit 0
fi

# Pass-through: user provides hashcat arguments. This script will not call any network services.
echo "Using hashcat at: $HASHCAT"
echo "Run hashcat with the arguments you supply. Example: --stdout -r tools/best64.rule inputs/wordlist.txt"

if [[ "$*" == *"--stdout"* ]]; then
  echo "Detected --stdout: capturing candidate stream to out/hashcat_candidates.txt"
  # Run hashcat and capture stdout to out/hashcat_candidates.txt
  $HASHCAT "$@" > out/hashcat_candidates.txt
  echo "Saved candidates to out/hashcat_candidates.txt"
  echo "Now running local solver against generated candidates..."
  # Deduplicate and feed into wordlist for the solver
  awk '!seen[$0]++' out/hashcat_candidates.txt > out/hashcat_candidates_uniq.txt
  cp out/hashcat_candidates_uniq.txt inputs/hashcat_candidates.txt
  python3 run_hash_solver.py --merkle
  echo "Solver completed. Check out/results.json and out/merkle_matches.json"
else
  echo "No --stdout provided. You may be attempting an active hashcat attack which we do not run automatically."
  echo "If you want to generate candidates to feed the solver, run hashcat with --stdout and then re-run this wrapper with --stdout included."
fi
