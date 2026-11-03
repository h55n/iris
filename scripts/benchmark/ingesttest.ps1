$ErrorActionPreference = 'Continue'
Set-Location D:\iris-test\iris
$env:IRIS_WHISPER_CLI = 'D:\iris-test\whisper-bin-x64\Release\whisper-cli.exe'
$log = 'D:\iris-test\bench\ingest.log'
"=== ingest tests start $(Get-Date -Format o) ===" | Tee-Object $log
"--- default model presence ---" | Tee-Object -Append $log
if (-not (Test-Path models\ggml-tiny.en.bin)) { curl.exe -sL -o models\ggml-tiny.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin }
Get-ChildItem models | Select-Object Name,Length | Format-Table | Out-String | Tee-Object -Append $log
"--- T3 record device enumeration (enumeration only, no capture) ---" | Tee-Object -Append $log
python iris\record.py --list-devices 2>&1 | Tee-Object -Append $log
"--- T1 cli ingest en_3min.wav backend ollama (default gemma3:4b) ---" | Tee-Object -Append $log
python -m iris.cli ingest D:\iris-test\bench\fleurs\en_us\en_3min.wav --backend ollama --title "win-pc ingest test" 2>&1 | Tee-Object -Append $log
"--- T6 ingest server header test ---" | Tee-Object -Append $log
python scripts\benchmark\servertest_win.py 2>&1 | Tee-Object -Append $log
"--- T7 webui serve check on Windows ---" | Tee-Object -Append $log
$w = Start-Process python -ArgumentList 'iris\webui.py','--port','8473' -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 4
$code = curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8473/
"webui GET / -> http $code" | Tee-Object -Append $log
Stop-Process -Id $w.Id -Force -ErrorAction SilentlyContinue
"=== ingest tests done $(Get-Date -Format o) ===" | Tee-Object -Append $log
