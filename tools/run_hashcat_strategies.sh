#!/usr/bin/env bash
set -euo pipefail

# Strategy runner: executes a list of conservative Hashcat candidate-generation strategies
# Each strategy has a name, a command (generally using --stdout or a short runtime) and a runtime budget.
# Collected candidates for each strategy are deduplicated and tested locally by the solver.
# This script does NOT perform any network access.

HASHCAT=$(command -v hashcat || true)
if [ -z "$HASHCAT" ]; then
  echo "hashcat not found in PATH. Install hashcat to use strategy runner." >&2
  exit 2
fi

OUT_DIR="out"
mkdir -p "$OUT_DIR"

STRATEGIES=(
  "wordlist_best64"
  "masks_short"
  "wordlist_combinator"
)

# Strategy commands (user can edit to tune locally)
# Use --stdout where possible to generate candidate lists rather than perform a full cracking run.
declare -A STRATEGY_CMD
STRATEGY_CMD[wordlist_best64]="$HASHCAT --stdout -r tools/best64.rule inputs/wordlist.txt"
STRATEGY_CMD[masks_short]="$HASHCAT --stdout ?l?l?l?l?d?d"
STRATEGY_CMD[wordlist_combinator]="$HASHCAT --stdout -a 1 inputs/wordlist.txt inputs/wordlist.txt"

# Runtime budget per strategy in seconds (used when calling non-stdout hashcat runs)
declare -A STRATEGY_TIME
STRATEGY_TIME[wordlist_best64]=60
STRATEGY_TIME[masks_short]=30
STRATEGY_TIME[wordlist_combinator]=45

RESULT_SUMMARY="$OUT_DIR/strategy_results.json"
echo '{}' > "$RESULT_SUMMARY"

for name in "${STRATEGIES[@]}"; do
  echo "Running strategy: $name"
  cmd=${STRATEGY_CMD[$name]}
  if [ -z "$cmd" ]; then
    echo "No command configured for strategy $name; skipping." >&2
    continue
  fi

  cand_file="$OUT_DIR/strategy_${name}_candidates.txt"

  # If command contains --stdout, run and capture candidates; otherwise run with runtime limit and read potfile
  if [[ "$cmd" == *"--stdout"* ]]; then
    echo "Executing: $cmd"
    # run and capture
    eval "$cmd" > "$cand_file" || true
  else
    pot="$OUT_DIR/strategy_${name}.pot"
    echo "Executing (runtime-limited): $cmd --potfile-path $pot --runtime ${STRATEGY_TIME[$name]}"
    eval "$cmd --potfile-path $pot --runtime ${STRATEGY_TIME[$name]}" || true
    if [ -f "$pot" ]; then
      cut -d ':' -f2- "$pot" > "$cand_file" || true
    fi
  fi

  if [ ! -f "$cand_file" ]; then
    echo "No candidates produced for strategy $name"
    continue
  fi

  # Deduplicate
  awk '!seen[$0]++' "$cand_file" > "${cand_file}.uniq"
  mv "${cand_file}.uniq" "$cand_file"
  echo "Strategy $name produced $(wc -l < "$cand_file") unique candidates"

  # Merge into inputs for solver (append then dedup)
  cat "$cand_file" >> inputs/hashcat_candidates.txt || true
  awk '!seen[$0]++' inputs/hashcat_candidates.txt > inputs/hashcat_candidates.tmp && mv inputs/hashcat_candidates.tmp inputs/hashcat_candidates.txt

  # Run solver against current candidate set
  python3 run_hash_solver.py --merkle

  # Record any matches produced into summary
  if [ -f out/results.json ]; then
    # store a copy of results.json per strategy
    cp out/results.json "$OUT_DIR/results_${name}.json"
    # annotate summary using jq if available, otherwise append simple text
    if command -v jq >/dev/null 2>&1; then
      jq --arg name "$name" '.[$name] = input' "$RESULT_SUMMARY" "$OUT_DIR/results_${name}.json" > "$RESULT_SUMMARY.tmp" && mv "$RESULT_SUMMARY.tmp" "$RESULT_SUMMARY" || true
    else
      echo "$name: $(wc -l < "$OUT_DIR/results_${name}.json") lines" >> "$RESULT_SUMMARY"
    fi
  fi

  echo "Completed strategy: $name"
done

echo "All strategies completed. See $OUT_DIR and $RESULT_SUMMARY for details."
