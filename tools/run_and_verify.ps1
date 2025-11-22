param(
    [string]$Hash
)

# Wrapper: run solver (optionally append a hash) then verify proofs using the Python verifier
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

# choose python
$py = "python"
if (Get-Command python3 -ErrorAction SilentlyContinue) { $py = "python3" }

if ($Hash) {
    Write-Host "Running solver with provided hash and verifying proof for $Hash"
    & .\tools\run_with_hash.ps1 -Hash $Hash
    Write-Host "Verifying proof for $Hash"
    & $py tools/verify_merkle.py --match-key $Hash
        Write-Host "Extracting URLs from outputs..."
        & $py tools/extract_urls.py
} else {
    Write-Host "Running solver without modifying inputs/hashes.txt"
    & .\tools\run_with_hash.ps1

    $matchesFile = Join-Path $repoRoot 'out/merkle_matches.json'
    if (Test-Path $matchesFile) {
        $json = Get-Content $matchesFile -Raw | ConvertFrom-Json
        foreach ($prop in $json.PSObject.Properties) {
            $k = $prop.Name
            Write-Host "Verifying match: $k"
            & $py tools/verify_merkle.py --match-key $k
        }
            Write-Host "Extracting URLs from outputs..."
            & $py tools/extract_urls.py
    } else {
        Write-Warning "No matches file found at $matchesFile"
    }
}

Write-Host "Run and verify complete. See out/ for artifacts."
