$ErrorActionPreference = 'Continue'
$m = 'D:\iris-test\iris\store\20261104-0431-dd3adf'
"=== T1 second-run store check ==="
"notes.md exists: $(Test-Path "$m\notes.md")"
"transcript.md exists: $(Test-Path "$m\transcript.md")"
"meta.json:"
Get-Content "$m\meta.json" -Raw
"--- ingest.log key lines (both runs) ---"
Select-String -Path D:\iris-test\bench\ingest.log -Pattern 'T1 cli|meeting:|backend:|integrity:|^notes:|encrypted:|cloud:|T6 ingest|T7 webui|webui GET' | ForEach-Object { $_.Line }
"=== starting webui for visual check (150s window) ==="
$p = Start-Process python -ArgumentList 'iris\webui.py','--port','8473' -PassThru -WorkingDirectory D:\iris-test\iris -WindowStyle Minimized
Start-Sleep -Seconds 6
$code = curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8473/
"webui GET / -> http $code"
if ($code -eq '200') { Start-Process 'http://127.0.0.1:8473/' }
Start-Sleep -Seconds 150
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
"=== verify2 done ==="
