@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Texture Pack Validator - Release Packager (Windows CMD)
REM Creates a distributable zip (excludes .venv, reports, __pycache__)

cd /d "%~dp0"

set TS=%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%-%TIME:~3,2%
set TS=%TS: =0%
set OUT=release_texture-pack-validator_!TS!.zip

echo Creating %OUT% ...

REM PowerShell is used ONLY for packaging (not required for running the tool)
powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$root=(Resolve-Path .).Path;" ^
  "$files=Get-ChildItem -Path $root -Recurse -File | Where-Object { " ^
  "  $_.FullName -notmatch '\\\\.venv\\\\' -and " ^
  "  $_.FullName -notmatch '\\\\reports\\\\' -and " ^
  "  $_.FullName -notmatch '\\\\__pycache__\\\\' -and " ^
  "  $_.Name -notmatch '\\.pyc$' " ^
  "};" ^
  "if(Test-Path $env:OUT){Remove-Item $env:OUT -Force};" ^
  "$tmp=New-Item -ItemType Directory -Force -Path (Join-Path $env:TEMP ('tpv_release_' + [guid]::NewGuid().ToString()));" ^
  "foreach($f in $files){ " ^
  "  $rel=$f.FullName.Substring($root.Length).TrimStart('\\');" ^
  "  $dst=Join-Path $tmp $rel;" ^
  "  New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null;" ^
  "  Copy-Item -LiteralPath $f.FullName -Destination $dst -Force" ^
  "};" ^
  "Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $env:OUT -Force;" ^
  "Remove-Item $tmp -Recurse -Force"

echo Done.
echo Output: %OUT%
endlocal
