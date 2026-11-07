import subprocess
ps = r'''
Get-Process | Where-Object { $_.ProcessName -match 'python|pythonw|FM2027|setup|ISCC' } | ForEach-Object {
  "{0} | PID {1} | {2:N0} Mo" -f $_.ProcessName, $_.Id, ($_.WorkingSet64/1MB)
}
'''
out = subprocess.run(['powershell','-NoProfile','-Command',ps], capture_output=True, text=True, errors='replace')
print(out.stdout.strip() or '(aucun processus python/FM2027/compilateur)')
if out.stderr.strip(): print('ERR:', out.stderr.strip())
