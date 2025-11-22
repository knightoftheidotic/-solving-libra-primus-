param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

# PowerShell wrapper to run Hashcat (if installed) and integrate its --stdout candidate output with the local solver.
# This script will NOT perform any network actions. It expects Hashcat to be installed locally.

$hashcat = Get-Command hashcat -ErrorAction SilentlyContinue
if (-not $hashcat) {
    Write-Error "hashcat not found in PATH. Install hashcat from https://hashcat.net/hashcat/ and rerun."
    exit 2
}

$out = Join-Path $PSScriptRoot '..\out' -Resolve
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

if ($Args -contains '--stdout') {
    Write-Host "Running hashcat with --stdout and capturing candidates to out/hashcat_candidates.txt"
    & hashcat @Args | Out-File -FilePath (Join-Path $out 'hashcat_candidates.txt') -Encoding utf8
    Write-Host "Deduplicating candidates and preparing inputs/hashcat_candidates.txt"
    $uniq = Get-Content (Join-Path $out 'hashcat_candidates.txt') | Select-Object -Unique
    $uniq | Set-Content -Path (Join-Path $PSScriptRoot '..\inputs\hashcat_candidates.txt') -Encoding utf8
    Write-Host "Running local solver (with --merkle) against generated candidates"
    & python3 run_hash_solver.py --merkle
    Write-Host "Solver finished. Check out/results.json and out/merkle_matches.json"
} else {
    Write-Host "No --stdout argument detected. To generate candidate lists for the solver, run hashcat with --stdout and rules/wordlists."
    Write-Host "This wrapper will not execute active cracking attacks automatically."
}
