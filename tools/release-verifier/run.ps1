\
Param(
  [Parameter(Mandatory=$true)][string]$ReleaseDir,
  [string]$Out = "audit_report.json",
  [switch]$AllowRevoked
)

$ErrorActionPreference = "Stop"

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip | Out-Null

if (Test-Path "requirements.lock.txt") {
  pip install -r requirements.lock.txt | Out-Null
} else {
  pip install -r requirements.txt | Out-Null
}

$ArgsList = @("--release-dir", $ReleaseDir, "--out", $Out)
if ($AllowRevoked) { $ArgsList += "--allow-revoked" }

python audit_verify.py @ArgsList
