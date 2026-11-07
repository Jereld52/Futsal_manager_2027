import subprocess
ps=r'''
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
  "{0} | {1} | WS={2,12} | {3}" -f $_.ProcessId,$_.CreationDate,$_.WorkingSetSize,$_.CommandLine
}
'''
out=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,errors='replace')
print(out.stdout)
print(out.stderr)
