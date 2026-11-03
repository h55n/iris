$ErrorActionPreference = 'Continue'
Set-Location D:\iris-test\iris
$cpu = (Get-CimInstance Win32_Processor).Name
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)
$env:MEASURED_ON = "hassan-pc hssn (Windows 11, $cpu, ${ram}GB RAM)"
$bench = 'D:\iris-test\bench'
$log = "$bench\bench.log"
"=== bench start $(Get-Date -Format o) ===" | Tee-Object $log
"CPU: $cpu" | Tee-Object -Append $log
"RAM: ${ram} GB" | Tee-Object -Append $log
"--- input wav check ---" | Tee-Object -Append $log
$wavs = Get-ChildItem D:\iris-test\bench\fleurs\hi_in\hi_hold30.wav, D:\iris-test\bench\fleurs\en_us\en_3min.wav -ErrorAction SilentlyContinue
$wavs | Select-Object Length,FullName | Format-Table -AutoSize | Out-String -Width 200 | Tee-Object -Append $log
if (($wavs | Where-Object Length -lt 1000000) -or $wavs.Count -lt 2) { "ABORT: input wav missing or too small" | Tee-Object -Append $log; exit 1 }
"--- whisper-cli smoke ---" | Tee-Object -Append $log
$cli = 'D:\iris-test\whisper-bin-x64\whisper-cli.exe'
if (-not (Test-Path $cli)) { $cli = (Get-ChildItem -Recurse D:\iris-test\whisper-bin-x64 -Filter whisper-cli.exe -ErrorAction SilentlyContinue | Select-Object -First 1).FullName }
"whisper-cli: $cli" | Tee-Object -Append $log
if (-not $cli) { "ABORT: whisper-cli.exe missing under D:\iris-test\whisper-bin-x64" | Tee-Object -Append $log; exit 1 }
& $cli -h 2>&1 | Select-Object -First 2 | Tee-Object -Append $log
"--- leg1 smoke: en_3min, ggml-small.bin, lang en, standard decode ---" | Tee-Object -Append $log
python scripts\benchmark\run_one_win.py D:\iris-test\bench\fleurs\en_us\en_3min.wav models\ggml-small.bin en D:\iris-test\bench\out_en3_small.json 0 2>&1 | Tee-Object -Append $log
python scripts\benchmark\wer.py D:\iris-test\bench\out_en3_small.json D:\iris-test\bench\fleurs\en_us\en_3min_ref.txt win-en3-small "windows pc smoke: en_us 3min, ggml-small, standard decode" https://huggingface.co/datasets/google/fleurs "CC BY 4.0" 2>&1 | Tee-Object -Append $log
"--- leg2: hi hold30, ggml-small.bin, lang auto, careful -mc 0 (validated config) ---" | Tee-Object -Append $log
python scripts\benchmark\run_one_win.py D:\iris-test\bench\fleurs\hi_in\hi_hold30.wav models\ggml-small.bin auto D:\iris-test\bench\out_hi_hold30_small_mc0.json 1 2>&1 | Tee-Object -Append $log
python scripts\benchmark\wer.py D:\iris-test\bench\out_hi_hold30_small_mc0.json D:\iris-test\bench\fleurs\hi_in\hi_hold30_ref.txt win-hi-hold30-small-mc0 "windows pc: hi_in hold30 25.7min, ggml-small, careful -mc 0" https://huggingface.co/datasets/google/fleurs "CC BY 4.0" 2>&1 | Tee-Object -Append $log
"=== bench done $(Get-Date -Format o) ===" | Tee-Object -Append $log
