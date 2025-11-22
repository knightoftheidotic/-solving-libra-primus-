param(
    [string]$Hash
)

# PowerShell helper to run the solver with an optional hash appended temporarily to `inputs/hashes.txt`.
# Usage:
#   .\run_with_hash.ps1 -Hash "<your-hash>"
# or
#   .\run_with_hash.ps1

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

# Decide which python to call (windows may use `python`)
$py = "python"
if (Get-Command python3 -ErrorAction SilentlyContinue) { $py = "python3" }

if ($Hash) {
    Write-Host "Appending provided hash to inputs/hashes.txt, running solver, then removing the appended line..."
    $hashFile = Join-Path $repoRoot "inputs/hashes.txt"
    Add-Content -Path $hashFile -Value $Hash
    & $py run_hash_solver.py --merkle
    # Remove last line if it equals the appended hash
    $lines = Get-Content $hashFile
    if ($lines.Count -gt 0 -and $lines[-1].Trim() -eq $Hash.Trim()) {
        $lines[0..($lines.Count - 2)] | Set-Content $hashFile
        Write-Host "Removed appended hash from inputs/hashes.txt"
    } else {
        Write-Warning "Appended hash not found at end of file; leaving file unchanged."
    }
} else {
    Write-Host "Running solver without modifying inputs/hashes.txt"
    & $py run_hash_solver.py --merkle
}

Write-Host "Run complete. Artifacts: out/results.json, out/merkle_root.txt, out/merkle_proofs.json, out/merkle_matches.json"
