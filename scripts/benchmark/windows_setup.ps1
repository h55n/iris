$ErrorActionPreference = 'Continue'
$log = 'D:\iris-test\stage1.log'
New-Item -ItemType Directory -Force D:\iris-test | Out-Null
Set-Location D:\iris-test
"=== stage1 start $(Get-Date -Format o) ===" | Tee-Object $log
Start-Process powershell -WindowStyle Minimized -ArgumentList '-NoProfile','-Command','ollama pull gemma3:4b *> D:\iris-test\ollama-pull.log'
"--- versions ---" | Tee-Object -Append $log
python --version 2>&1 | Tee-Object -Append $log
git --version 2>&1 | Tee-Object -Append $log
(ffmpeg -version 2>&1 | Select-Object -First 1) | Tee-Object -Append $log
ollama list 2>&1 | Tee-Object -Append $log
"--- clone ---" | Tee-Object -Append $log
if (-not (Test-Path D:\iris-test\iris)) { git clone --depth 1 https://github.com/h55n/iris.git D:\iris-test\iris 2>&1 | Tee-Object -Append $log }
Set-Location D:\iris-test\iris
"--- pip ---" | Tee-Object -Append $log
python -m pip install --quiet numpy jiwer 2>&1 | Tee-Object -Append $log
"--- whisper.cpp binary ---" | Tee-Object -Append $log
if (-not (Test-Path D:\iris-test\whisper-bin-x64\whisper-cli.exe)) {
  # v1.9.1 is the last release shipping prebuilt Windows binaries (v1.9.5+ ships none)
  curl.exe -sL -o D:\iris-test\whisper-bin-x64.zip https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-bin-x64.zip
  Expand-Archive -Force D:\iris-test\whisper-bin-x64.zip D:\iris-test\whisper-bin-x64
}
Get-ChildItem -Recurse D:\iris-test\whisper-bin-x64 -Filter whisper-cli.exe | Select-Object -ExpandProperty FullName | Tee-Object -Append $log
"--- models ---" | Tee-Object -Append $log
New-Item -ItemType Directory -Force models | Out-Null
if (-not (Test-Path models\ggml-base.en.bin)) { curl.exe -sL -o models\ggml-base.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin }
if (-not (Test-Path models\ggml-small.bin)) { curl.exe -sL -o models\ggml-small.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin }
if (-not (Test-Path models\ggml-silero-v6.2.0.bin)) { curl.exe -sL -o models\ggml-silero-v6.2.0.bin https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin }
Get-ChildItem models | Select-Object Name,Length | Tee-Object -Append $log
"--- fleurs hi_in ---" | Tee-Object -Append $log
New-Item -ItemType Directory -Force D:\iris-test\bench\fleurs\hi_in | Out-Null
Set-Location D:\iris-test\bench\fleurs
if (-not (Test-Path hi_in.test.tsv)) { curl.exe -sL -o hi_in.test.tsv https://huggingface.co/datasets/google/fleurs/resolve/main/data/hi_in/test.tsv }
if (-not (Test-Path hi_in.test.tar.gz)) { curl.exe -sL -o hi_in.test.tar.gz https://huggingface.co/datasets/google/fleurs/resolve/main/data/hi_in/audio/test.tar.gz }
Set-Location hi_in
tar xzf ..\hi_in.test.tar.gz
python D:\iris-test\iris\scripts\benchmark\fleurs_concat.py ..\hi_in.test.tsv test 30 hi_hold30.wav hi_hold30_ref.txt 30,15
"--- fleurs en_us ---" | Tee-Object -Append $log
New-Item -ItemType Directory -Force D:\iris-test\bench\fleurs\en_us | Out-Null
Set-Location D:\iris-test\bench\fleurs
if (-not (Test-Path en_us.test.tsv)) { curl.exe -sL -o en_us.test.tsv https://huggingface.co/datasets/google/fleurs/resolve/main/data/en_us/test.tsv }
if (-not (Test-Path en_us.test.tar.gz)) { curl.exe -sL -o en_us.test.tar.gz https://huggingface.co/datasets/google/fleurs/resolve/main/data/en_us/audio/test.tar.gz }
Set-Location en_us
tar xzf ..\en_us.test.tar.gz
python D:\iris-test\iris\scripts\benchmark\fleurs_concat.py ..\en_us.test.tsv test 3 en_3min.wav en_3min_ref.txt
"=== stage1 done $(Get-Date -Format o) ===" | Tee-Object -Append $log
