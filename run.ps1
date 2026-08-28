# Windows PowerShell wrapper. The real launcher is run.py (same launcher on every OS).
# If PowerShell blocks this script, use  .\run.cmd  or  python run.py  instead.
Set-Location $PSScriptRoot
if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 run.py @args }
else { & python run.py @args }
