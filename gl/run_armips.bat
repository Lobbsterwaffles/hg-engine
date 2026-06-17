@echo off
REM Run armips through MSYS2
REM Usage: run_armips.bat <assembly_file>

set MSYS2_PATH=C:\msys64
set HG_ENGINE_PATH=%~dp0..

if "%~1"=="" (
    echo Usage: run_armips.bat ^<assembly_file^>
    exit /b 1
)

REM Convert Windows path to MSYS2 path
set "ASM_FILE=%~1"
set "ASM_FILE=%ASM_FILE:\=/%"
set "ASM_FILE=%ASM_FILE:C:=/c%"

REM Run armips in MSYS2 environment
%MSYS2_PATH%\usr\bin\bash.exe -lc "cd '%HG_ENGINE_PATH:\=/%' && ./tools/armips '%ASM_FILE%'"
