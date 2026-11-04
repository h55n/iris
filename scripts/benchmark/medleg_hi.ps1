$ErrorActionPreference='Continue'
$log='D:\iris-test\medleghi.log'
"start $(Get-Date -Format o)" | Tee-Object $log
Get-PSDrive D | ForEach-Object { "D free GB: {0}" -f [math]::Round($_.Free/1GB,1) } | Tee-Object -Append $log
$cli = Get-ChildItem -Recurse D:\iris-test\whisper-bin-x64 -Filter whisper-cli.exe | Select-Object -First 1 -ExpandProperty FullName
"cli=$cli" | Tee-Object -Append $log
$mdir='D:\iris-test\iris\models'
$m = Join-Path $mdir 'ggml-medium.bin'
if (-not (Test-Path $m) -or (Get-Item $m).Length -ne 1533763059) {
  "downloading medium..." | Tee-Object -Append $log
  curl.exe -L -o $m https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin 2>&1 | Select-Object -Last 3 | Tee-Object -Append $log
}
"size=$((Get-Item $m).Length)" | Tee-Object -Append $log
$h = (Get-FileHash $m -Algorithm SHA256).Hash.ToLower()
"sha256=$h" | Tee-Object -Append $log
if ($h -ne '6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208') { "HASH MISMATCH - aborting" | Tee-Object -Append $log; exit 1 }
$sil = Join-Path $mdir 'ggml-silero-v6.2.0.bin'
$wavdir = 'D:\iris-test\bench\fleurs\hi_in\test'
$out = 'D:\iris-test\wer-attr\out-med-hi'
New-Item -ItemType Directory -Force $out | Out-Null
$clips = @('10011266027513218401','10014385262415025488','10015817292782645020','10027305580492162464','10069289676238419279','10107687492910459268','10128382631186456345','10135688561274120767','10200643191519059428','10245365873747218908','10286778291956788434','10291152526359423424','10359991159058879218','10550791631951016124','10582204498174558997','10587318592827006604','10590937942465254187','10622951485514869484','10761312360331088376','1078154098564425938','10798430940133763019','10847487616323903195','10907654079731428081','10921902647446458507','10924000697500767031','10972260827293009900','10980788482676060439','11014623647783711221','11044357197343438539','11063307654961399321')
foreach ($c in $clips) {
  $w = Join-Path $wavdir ($c + '.wav')
  if (Test-Path (Join-Path $out ($c + '.json'))) { "skip $c" | Tee-Object -Append $log; continue }
  if (-not (Test-Path $w)) { "MISSING $w" | Tee-Object -Append $log; continue }
  $t0 = Get-Date
  & $cli -m $m -f $w -l hi -oj -of (Join-Path $out $c) --vad -vm $sil -vmsd 10 -mc 0 *> $null
  $dt = [math]::Round(((Get-Date)-$t0).TotalSeconds,1)
  "done $c ${dt}s" | Tee-Object -Append $log
}
"ALLDONE $(Get-Date -Format o)" | Tee-Object -Append $log
