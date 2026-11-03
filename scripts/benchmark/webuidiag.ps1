$ErrorActionPreference = 'Continue'
Set-Location D:\iris-test\iris
$log = 'D:\iris-test\bench\webuidiag.log'
"=== webui diag start $(Get-Date -Format o) ===" | Tee-Object $log
"cwd: $(Get-Location)" | Tee-Object -Append $log
"store exists: $(Test-Path store)" | Tee-Object -Append $log
$out = 'D:\iris-test\bench\webui.out.log'
$err = 'D:\iris-test\bench\webui.err.log'
Remove-Item $out,$err -ErrorAction SilentlyContinue
$p = Start-Process python -ArgumentList 'iris\webui.py','--port','8473' -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
"started pid $($p.Id)" | Tee-Object -Append $log
Start-Sleep -Seconds 8
"process alive after 8s: $(-not $p.HasExited)" | Tee-Object -Append $log
if ($p.HasExited) { "exit code: $($p.ExitCode)" | Tee-Object -Append $log }
$code = curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8473/
"webui GET / -> http $code" | Tee-Object -Append $log
"--- stdout ---" | Tee-Object -Append $log
Get-Content $out -ErrorAction SilentlyContinue | Tee-Object -Append $log
"--- stderr ---" | Tee-Object -Append $log
Get-Content $err -ErrorAction SilentlyContinue | Tee-Object -Append $log
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
"=== diag done ===" | Tee-Object -Append $log
