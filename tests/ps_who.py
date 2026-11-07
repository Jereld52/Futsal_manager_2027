import subprocess
for pid in (11076, 9760):
    ps = 'Get-CimInstance Win32_Process -Filter "ProcessId=%d" | Select-Object ProcessId,CreationDate,CommandLine | Format-List' % pid
    out = subprocess.run(['powershell','-NoProfile','-Command',ps], capture_output=True, text=True, errors='replace')
    print(out.stdout)

# Et tout processus avec CPU consommé
ps2 = 'Get-Process | Sort-Object CPU -Descending | Select-Object -First 8 ProcessName,Id,CPU | Format-Table -AutoSize'
out = subprocess.run(['powershell','-NoProfile','-Command',ps2], capture_output=True, text=True, errors='replace')
print(out.stdout)
