$ErrorActionPreference = 'Continue'
$out = 'C:\Users\hassa\Desktop\recon-out.txt'
"=== recon $(Get-Date -Format o) ===" | Tee-Object $out
"--- psdrives ---" | Tee-Object -Append $out
Get-PSDrive -PSProvider FileSystem | Select-Object Name,@{n='FreeGB';e={[math]::Round($_.Free/1GB,2)}},@{n='UsedGB';e={[math]::Round($_.Used/1GB,2)}} | Format-Table | Out-String | Tee-Object -Append $out
"--- stage1.log tail ---" | Tee-Object -Append $out
Get-Content D:\iris-test\stage1.log -Tail 30 -ErrorAction SilentlyContinue | Tee-Object -Append $out
"--- ollama-pull.log tail ---" | Tee-Object -Append $out
Get-Content D:\iris-test\ollama-pull.log -Tail 4 -ErrorAction SilentlyContinue | Tee-Object -Append $out
"--- ollama model store ---" | Tee-Object -Append $out
foreach ($s in @('C:\Users\hassa\.ollama\models','D:\.ollama\models')) { if (Test-Path $s) { $sz = (Get-ChildItem $s -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; "$s exists, $([math]::Round($sz/1GB,2)) GB" | Tee-Object -Append $out } else { "$s MISSING" | Tee-Object -Append $out } }
"OLLAMA_MODELS env: '$env:OLLAMA_MODELS'" | Tee-Object -Append $out
"--- processes ---" | Tee-Object -Append $out
Get-Process ffmpeg,python,curl,tar,ollama,whisper-cli -ErrorAction SilentlyContinue | Select-Object Name,Id,CPU,StartTime | Format-Table | Out-String | Tee-Object -Append $out
"--- newest files in D:\iris-test ---" | Tee-Object -Append $out
Get-ChildItem D:\iris-test -Recurse -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 15 LastWriteTime,Length,FullName | Format-Table -AutoSize | Out-String -Width 220 | Tee-Object -Append $out
"=== recon done ===" | Tee-Object -Append $out
