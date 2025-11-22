param(
    [int]$HashType = 0,
    [int]$AttackMode = 0,
    [int]$Runtime = 300,
    [string]$HashFile = 'inputs/hashes.txt',
    [string]$Wordlist = 'inputs/wordlist.txt',
    [string]$Rules = 'tools/best64.rule',
    [string]$OutDir = 'out'
)

# PowerShell wrapper for controlled Hashcat attacks.
if (-not (Get-Command hashcat -ErrorAction SilentlyContinue)) {
    Write-Error "hashcat not found in PATH. Install it to run attacks."
    exit 2
}

$out = Resolve-Path (Join-Path $PSScriptRoot "..\$OutDir")
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

$pot = Join-Path $out 'hashcat_attack.potfile'
$cand = Join-Path $out 'hashcat_attack_candidates.txt'

Write-Host "Running hashcat (safe wrapper): hash-type $HashType, attack-mode $AttackMode, runtime ${Runtime}s"

if ($AttackMode -eq 0) {
    if (Test-Path $Rules) {
        & hashcat -m $HashType -a 0 $HashFile $Wordlist -r $Rules --potfile-path $pot --runtime $Runtime
    } else {
        & hashcat -m $HashType -a 0 $HashFile $Wordlist --potfile-path $pot --runtime $Runtime
    }
} else {
    & hashcat -m $HashType -a $AttackMode $HashFile $Wordlist --potfile-path $pot --runtime $Runtime
}

if (Test-Path $pot) {
    Get-Content $pot | ForEach-Object { $_ -split ':' , 2 } | ForEach-Object { $_[1] } | Where-Object { $_ -ne '' } | Select-Object -Unique | Set-Content $cand
    Write-Host "Wrote candidates to $cand"
    Copy-Item $cand -Destination (Join-Path $PSScriptRoot '..\inputs\hashcat_candidates.txt') -Force
    Write-Host "Running local solver on generated candidates..."
    & python3 run_hash_solver.py --merkle
    Write-Host "Solver complete. See out/results.json and out/merkle_matches.json"
} else {
    Write-Warning "No potfile found; no candidates produced."
}
