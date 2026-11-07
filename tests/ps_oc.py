import subprocess
#溺水 correction : pas d'opérateur ?? (PS5)
ps = r'''
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'opencode|node|bun' } | ForEach-Object {
  $cl = '' + $_.CommandLine
  if ($cl.Length -gt 160) { $cl = $cl.Substring(0,160) }
  "PID {0} | {1} | {2} | {3}" -f $_.ProcessId, $_.CreationDate, $_.Name, $cl
}
Get-Process | Where-Object { $_.ProcessName -match 'opencode' } | ForEach-Object {
  "PROC {0} PID {1} CPU {2:N0}" -f $_.ProcessName, $_.Id, $_.CPU
}
'''
out = subprocess.run(['powershell','-NoProfile','-Command',ps], capture_output=True, text=True, errors='replace')
txt = out.stdout.strip()
print(txt if txt else '(aucun processus opencode/node/bun)')
if out.stderr.strip(): print('ERR:', out.stderr.strip()[:300])
