# Windows PowerShell wrapper for the day-2 failure injector.
# If PowerShell blocks this script, use  .\inject.cmd  instead.
Set-Location $PSScriptRoot
if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m harness.inject @args }
else { & python -m harness.inject @args }
