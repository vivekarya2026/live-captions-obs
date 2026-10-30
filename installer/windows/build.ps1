# Builds dist\LiveCaptions-<version>-Windows-x64-Setup.exe (run on Windows; used by GitHub Actions).
#   powershell -ExecutionPolicy Bypass -File installer\windows\build.ps1
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path "$Here\..\.."
$Version = (Select-String -Path "$Root\app\livecaptions\__init__.py" -Pattern '__version__ = "(.*)"').Matches[0].Groups[1].Value
$PbsTag = "20261026"
$PyVersion = "3.11.18"
$Tarball = "cpython-$PyVersion+$PbsTag-x86_64-pc-windows-msvc-install_only.tar.gz"
$Url = "https://github.com/astral-sh/python-build-standalone/releases/download/$PbsTag/$Tarball"
$Build = "$Root\build\windows"
$Cache = "$Root\build\cache"

Write-Host "== Live Captions $Version for Windows"
if (Test-Path $Build) { Remove-Item -Recurse -Force $Build }
New-Item -ItemType Directory -Force -Path $Build, $Cache, "$Root\dist" | Out-Null

if (-not (Test-Path "$Cache\$Tarball")) {
  Write-Host "-- downloading Python $PyVersion"
  Invoke-WebRequest -Uri $Url -OutFile "$Cache\$Tarball"
}
tar -xzf "$Cache\$Tarball" -C $Build           # -> build\windows\python
$Py = "$Build\python\python.exe"
Write-Host "-- installing packages"
& $Py -m pip install --quiet --disable-pip-version-check --no-cache-dir --no-warn-script-location -r "$Root\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "pip failed" }
foreach ($d in "Lib\test", "Lib\idlelib", "Lib\tkinter", "Lib\turtledemo", "tcl") {
  if (Test-Path "$Build\python\$d") { Remove-Item -Recurse -Force "$Build\python\$d" }
}
Get-ChildItem -Path "$Build\python" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

New-Item -ItemType Directory -Force -Path "$Build\app" | Out-Null
Copy-Item -Recurse "$Root\app\livecaptions" "$Build\app\livecaptions"
Get-ChildItem -Path "$Build\app" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Copy-Item -Recurse "$Root\obs" "$Build\obs"
Copy-Item "$Root\LICENSE" "$Build\LICENSE.txt"
& $Py -m compileall -q "$Build\app" | Out-Null

# Quick check that the bundled Python can load the app
Push-Location "$Build\app"
& $Py -c "import livecaptions.translator, livecaptions.gdocs, ctranslate2, sounddevice; print('imports ok')"
if ($LASTEXITCODE -ne 0) { throw "import check failed" }
Pop-Location

$Iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $Iscc) { $Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
& $Iscc "/DAppVersion=$Version" "/DBuildDir=$Build" "/DOutDir=$Root\dist" "$Here\LiveCaptions.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
Write-Host "== built dist\LiveCaptions-$Version-Windows-x64-Setup.exe"
