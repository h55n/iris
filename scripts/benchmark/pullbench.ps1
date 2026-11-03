$ErrorActionPreference = 'Continue'
Set-Location D:\iris-test\iris
git pull 2>&1
git log --oneline -1
powershell -ExecutionPolicy Bypass -File D:\iris-test\iris\scripts\benchmark\bench.ps1
