# Serves the static UI (index.html, data/, etc.) at http://localhost:8385/
# Run after reboot:  powershell -ExecutionPolicy Bypass -File .\serve.ps1
Set-Location $PSScriptRoot
Write-Host "Open http://localhost:8385/  (Ctrl+C to stop)" -ForegroundColor Green
python -m http.server 8385
