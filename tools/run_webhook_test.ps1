<#
.SYNOPSIS
  Start the local webhook receiver, send a signed test webhook, and show outputs.

.DESCRIPTION
  This script is intended to be run on a VM you control (PowerShell).
  It starts `webhook_receiver.py` in the background (inherits env vars),
  signs and sends a test webhook using `tools/sign_webhook.py`, waits for
  the solver to run (if configured), prints `out/` artifacts, and stops
  the webhook server.

USAGE
  From the repository root (where `webhook_receiver.py` lives):
    pwsh ./tools/run_webhook_test.ps1

  Optional parameters:
    -Port <int>          (default 9000)
    -PayloadFile <path>  (default tools/test_payload.json)
    -UseTor              (switch; runs with USE_TOR=1)

NOTES
  - This is for local, controlled testing only. Do not run against
    systems you are not authorized to contact.
  - Ensure Python is in PATH and you have installed requirements.
#>

param(
  [int]$Port = 9000,
  [string]$PayloadFile = "tools/test_payload.json",
  [switch]$UseTor,
  [string]$Hash = ""
)

# If set, write the supplied hash directly to inputs/hashes.txt and run the solver locally.
[switch]$AddDirectly = $false

function Show-Header($s) { Write-Host "`n=== $s ===`n" -ForegroundColor Cyan }

Push-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
Pop-Location

# Ensure running from repo root
Set-Location -Path (Resolve-Path "..").Path

Show-Header "Environment setup"
$env:WEBHOOK_SECRET = $env:WEBHOOK_SECRET -or "test-secret"
$env:PROCESS_WEBHOOK = "1"
$env:ENABLE_NETWORK = "1"
if ($UseTor) { $env:USE_TOR = "1" } else { $env:USE_TOR = "0" }
$env:WORKING_DIR = (Get-Location).Path

Write-Host "WEBHOOK_SECRET=$($env:WEBHOOK_SECRET)"
Write-Host "PROCESS_WEBHOOK=$($env:PROCESS_WEBHOOK)"
Write-Host "ENABLE_NETWORK=$($env:ENABLE_NETWORK)"
Write-Host "USE_TOR=$($env:USE_TOR)"

Show-Header "Ensure payload exists"
if (-Not (Test-Path $PayloadFile)) {
  New-Item -ItemType Directory -Force -Path (Split-Path $PayloadFile) | Out-Null
}

# If AddDirectly is set, append the provided hash to inputs/hashes.txt (deduplicated)
if ($AddDirectly -and $Hash -ne "") {
  Show-Header "Adding hash directly to inputs/hashes.txt"
  $inputsDir = "inputs"
  if (-Not (Test-Path $inputsDir)) { New-Item -ItemType Directory -Force -Path $inputsDir | Out-Null }
  $hashesFile = Join-Path $inputsDir "hashes.txt"
  $existing = @()
  if (Test-Path $hashesFile) { $existing = Get-Content -Path $hashesFile -ErrorAction SilentlyContinue }
  $hLower = $Hash.ToLower()
  if ($existing -notcontains $hLower) {
    Add-Content -Path $hashesFile -Value $hLower
    Write-Host "Appended hash to $hashesFile: $hLower"
  } else {
    Write-Host "Hash already present in $hashesFile"
  }

  # Run the solver directly and show outputs
  Show-Header "Running solver directly"
  & python run_hash_solver.py
  Show-Header "Outputs in out/"
  if (Test-Path out) {
    Get-ChildItem -Path out | ForEach-Object {
      Write-Host "-- $($_.Name) --"
      try { Get-Content -Raw -Path $_.FullName | Write-Host } catch { Write-Host "(binary or unreadable)" }
    }
  } else {
    Write-Host "No out/ directory found"
  }

  Write-Host "Done (direct add + solver run). Exiting."
  return
}

# Build payload. If a hash was provided, include it in the `content` field so the webhook
# receiver will extract it and add it to `inputs/hashes.txt`.
$payloadObj = @{ test = "webhook"; ts = 0 }
if ($Hash -ne "") {
  $payloadObj.content = "Found puzzle hash: $Hash"
}
$json = $payloadObj | ConvertTo-Json -Compress
$json | Out-File -Encoding utf8 -FilePath $PayloadFile
Write-Host "Created payload at $PayloadFile: $json"

Show-Header "Starting webhook receiver"
# Start the webhook server; it will inherit the env vars set above
$proc = Start-Process -FilePath python -ArgumentList "webhook_receiver.py --port $Port" -NoNewWindow -PassThru
Write-Host "Started webhook_receiver.py (PID $($proc.Id)). Waiting briefly..."
Start-Sleep -Seconds 2

Show-Header "Signing payload"
$sig = & python tools/sign_webhook.py --secret $env:WEBHOOK_SECRET --file $PayloadFile
Write-Host "Signature: $sig"

Show-Header "Sending webhook to http://localhost:$Port/webhook"
$body = Get-Content -Raw -Encoding UTF8 $PayloadFile
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:$Port/webhook" -Method Post -Body $body -Headers @{"Content-Type"="application/json"; "X-Signature"=$sig} -UseBasicParsing -TimeoutSec 30
    Write-Host "Response status: $($resp.StatusCode)"
} catch {
    Write-Host "Request failed: $_"
}

Show-Header "Waiting for solver to run (if triggered)"
Start-Sleep -Seconds 4

Show-Header "Outputs in out/"
if (Test-Path out) {
    Get-ChildItem -Path out | ForEach-Object {
        Write-Host "-- $($_.Name) --"
        try { Get-Content -Raw -Path $_.FullName | Write-Host } catch { Write-Host "(binary or unreadable)" }
    }
} else {
    Write-Host "No out/ directory found"
}

Show-Header "Stopping webhook receiver (PID $($proc.Id))"
try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch { }

Write-Host "Done. Inspect the files under out/ for results and logs."
