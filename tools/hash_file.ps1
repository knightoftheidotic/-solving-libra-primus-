param(
    [string]$FilePath
)

if (-not $FilePath) {
    Write-Host "Usage: .\tools\hash_file.ps1 -FilePath C:\path\to\candidate10.txt"
    exit 2
}

$p = Resolve-Path $FilePath -ErrorAction SilentlyContinue
if (-not $p) {
    Write-Error "File not found: $FilePath"
    exit 2
}

$bytes = [System.IO.File]::ReadAllBytes($p)
$sha1 = [System.BitConverter]::ToString((New-Object System.Security.Cryptography.SHA1Managed).ComputeHash($bytes)).Replace('-', '').ToLower()
$sha256 = [System.BitConverter]::ToString((New-Object System.Security.Cryptography.SHA256Managed).ComputeHash($bytes)).Replace('-', '').ToLower()
$sha512 = [System.BitConverter]::ToString((New-Object System.Security.Cryptography.SHA512Managed).ComputeHash($bytes)).Replace('-', '').ToLower()

$log = Join-Path $p.Parent ($p.BaseName + '_hash_log.txt')
"File: $p" | Out-File -FilePath $log -Encoding utf8
"Timestamp: $(Get-Date -AsUTC)" | Out-File -FilePath $log -Append -Encoding utf8
"SHA1: $sha1" | Out-File -FilePath $log -Append -Encoding utf8
"SHA256: $sha256" | Out-File -FilePath $log -Append -Encoding utf8
"SHA512: $sha512" | Out-File -FilePath $log -Append -Encoding utf8

Write-Host "Hashing $($p.BaseName) complete. Results saved in $log"
Write-Host "SHA1: $sha1"
Write-Host "SHA256: $sha256"
Write-Host "SHA512: $sha512"
