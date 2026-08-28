@echo off
REM Windows wrapper for the day-2 failure injector.  .\inject.cmd --help
setlocal
cd /d "%~dp0"
set "PYEXE=python"
where py >nul 2>nul && set "PYEXE=py -3"
%PYEXE% -m harness.inject %*
