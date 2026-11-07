import subprocess
ps = r'''
Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe' OR Name='cmd.exe'" | ForEach-Object {
  "PID {0} | {1} | {2}" -f $_.ProcessId, $_.CreationDate, $_.CommandLine
}
'''
out = subprocess.run(['powershell','-NoProfile','-Command',ps], capture_output=True, text=True, errors='replace')
txt = out.stdout.strip()
print(txt if txt else '(aucun powershell/cmd)')
if out.stderr.strip(): print('ERR:', out.stderr.strip())
