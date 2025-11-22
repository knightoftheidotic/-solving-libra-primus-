param()

# PowerShell strategy runner for Hashcat
# Runs a set of conservative, time-bounded strategies (via --stdout or short runs),
# collects candidates and feeds them into the local solver for verification.

if (-not (Get-Command hashcat -ErrorAction SilentlyContinue)) {
    Write-Error "hashcat not found in PATH. Install hashcat to use the strategy runner."
    exit 2
}

$out = Resolve-Path (Join-Path $PSScriptRoot '..\out')
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

$strategies = @(
    @{ name = 'wordlist_best64'; cmd = "hashcat --stdout -r tools/best64.rule inputs/wordlist.txt"; time = 60 },
    @{ name = 'masks_short'; cmd = "hashcat --stdout ?l?l?l?l?d?d"; time = 30 },
    @{ name = 'wordlist_combinator'; cmd = "hashcat --stdout -a 1 inputs/wordlist.txt inputs/wordlist.txt"; time = 45 }
)

$resultSummary = Join-Path $out 'strategy_results.json'
"{}" | Out-File -FilePath $resultSummary -Encoding utf8

foreach ($s in $strategies) {
    $name = $s.name
    $cmd = $s.cmd
    $cand = Join-Path $out "strategy_${name}_candidates.txt"
    Write-Host "Running strategy: $name -> $cmd"

    if ($cmd -match '--stdout') {
        Invoke-Expression $cmd | Out-File -FilePath $cand -Encoding utf8
    } else {
        $pot = Join-Path $out "strategy_${name}.pot"
        Invoke-Expression "$cmd --potfile-path $pot --runtime $($s.time)"
        if (Test-Path $pot) {
            Get-Content $pot | ForEach-Object { ($_ -split ':',2)[1] } | Where-Object { $_ -ne '' } | Set-Content $cand
        }
    }

    if (-not (Test-Path $cand)) {
        Write-Warning "No candidates produced for $name"
        continue
    }

    # Deduplicate
    Get-Content $cand | Select-Object -Unique | Set-Content $cand
    Write-Host "Strategy $name produced $(Get-Content $cand | Measure-Object -Line).Lines unique candidates"

    Copy-Item $cand -Destination (Join-Path $PSScriptRoot '..\inputs\hashcat_candidates.txt') -Force

    Write-Host "Running local solver against generated candidates..."
    & python3 run_hash_solver.py --merkle

    if (Test-Path (Join-Path $out 'results.json')) {
        Copy-Item (Join-Path $out 'results.json') -Destination (Join-Path $out "results_${name}.json") -Force
        # add to summary (simple append)
        Add-Content -Path $resultSummary -Value "`n# $name results saved to out/results_${name}.json"
    }
}

Write-Host "All strategies completed. See $out and $resultSummary for details."
