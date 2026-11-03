$ErrorActionPreference = 'Continue'
Set-Location D:\iris-test\iris
"--- git pull ---"
git pull 2>&1
git log --oneline -1
"--- rerun setup (idempotent) ---"
powershell -ExecutionPolicy Bypass -File .\scripts\benchmark\windows_setup.ps1
"--- wav sizes ---"
Get-ChildItem D:\iris-test\bench\fleurs -Recurse -Filter *.wav | Select-Object Length,FullName | Format-Table -AutoSize | Out-String -Width 200
"=== runner done ==="
