@echo off
REM Windows wrapper. The real launcher is run.py (same launcher on every OS).
REM   .\run.cmd            everything on this machine
REM   .\run.cmd board      just the board, for the team to point at
REM   .\run.cmd mine assigner-A
REM   .\run.cmd fresh      wipe board.db first
setlocal
cd /d "%~dp0"
set "PYEXE=python"
where py >nul 2>nul && set "PYEXE=py -3"
%PYEXE% run.py %*
