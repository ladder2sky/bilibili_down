Param(
  [string]$WingetId = $(if ($env:FFMPEG_WINGET_ID) { $env:FFMPEG_WINGET_ID } else { "Gyan.FFmpeg" })
)
$ErrorActionPreference = 'Stop'
function Test-Ffmpeg { if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { return $true } else { return $false } }
if (Test-Ffmpeg) { ffmpeg -version; exit 0 }
$hasWinget = (Get-Command winget -ErrorAction SilentlyContinue) -ne $null
if (-not $hasWinget) { Write-Host "winget not found"; exit 1 }
winget install --id $WingetId -e --accept-package-agreements --accept-source-agreements | Out-Host
if (Test-Ffmpeg) { ffmpeg -version; exit 0 }
$candidates = @(
  (Join-Path $env:ProgramFiles 'ffmpeg\bin\ffmpeg.exe'),
  (Join-Path $env:ProgramFiles 'FFmpeg\bin\ffmpeg.exe'),
  (Join-Path $env:ProgramFiles 'Gyan\FFmpeg\bin\ffmpeg.exe')
)
foreach ($c in $candidates) { if (Test-Path $c) { $dir = Split-Path $c -Parent; $env:Path = $dir + ';' + $env:Path; if (Test-Ffmpeg) { ffmpeg -version; exit 0 } } }
Write-Host "ffmpeg not found after install"; exit 1
