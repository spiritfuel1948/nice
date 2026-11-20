# ============================================================
#  Local AI Team - one-click installer for Windows 10/11
#  Installs: Ollama (engine), AI models, Open WebUI (chat in your
#  browser), VS Code + Continue (coding helper).
#  Everything is free and runs on your own PC.
# ============================================================

$ErrorActionPreference = 'Continue'
$Root = Join-Path $env:USERPROFILE 'LocalAI'
New-Item -ItemType Directory -Force -Path $Root | Out-Null

function Say($msg)  { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    WARNING: $msg" -ForegroundColor Yellow }

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

function Winget-Install($id, $name) {
    Say "Installing $name"
    winget install --id $id -e --silent --accept-source-agreements --accept-package-agreements
    Refresh-Path
}

# ---------- 0. Checks ----------
Say 'Checking your PC'
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host 'winget is missing. Install "App Installer" from the Microsoft Store, then run this again.' -ForegroundColor Red
    exit 1
}
$freeGB = [math]::Round((Get-PSDrive -Name ($env:USERPROFILE.Substring(0,1))).Free / 1GB)
Ok "Free disk space: $freeGB GB (about 60 GB is needed for everything)"

# ---------- 1. Ollama (the engine) ----------
$ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
if (-not (Test-Path $ollama)) { Winget-Install 'Ollama.Ollama' 'Ollama' }
if (-not (Test-Path $ollama)) {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { $ollama = $cmd.Source }
}
if (-not (Test-Path $ollama)) { Write-Host 'Ollama did not install. Get it from ollama.com and run this again.' -ForegroundColor Red; exit 1 }
Ok 'Ollama installed'

function Ollama-Running {
    try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}
if (-not (Ollama-Running)) {
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not (Ollama-Running); $i++) { Start-Sleep -Seconds 1 }
}
if (Ollama-Running) { Ok 'Ollama is running' } else { Warn 'Ollama did not start; model downloads may fail' }

# ---------- 2. Models ----------
# name, approx size GB, what it is for
$models = @(
    @('qwen3:14b',          9,  'everyday chat'),
    @('deepseek-r1:14b',    9,  'step-by-step reasoning'),
    @('qwen2.5-coder:14b',  9,  'coding'),
    @('qwen2.5-coder:1.5b', 1,  'code autocomplete'),
    @('nomic-embed-text',   1,  'searching your documents'),
    @('qwen3:30b',          19, 'smarter answers (uses your RAM)')
)
foreach ($m in $models) {
    $freeGB = [math]::Round((Get-PSDrive -Name ($env:USERPROFILE.Substring(0,1))).Free / 1GB)
    if ($freeGB -lt ($m[1] + 10)) { Warn "Skipping $($m[0]) - not enough disk space"; continue }
    Say "Downloading model $($m[0]) (~$($m[1]) GB) for $($m[2])"
    & $ollama pull $m[0]
    if ($LASTEXITCODE -eq 0) { Ok $m[0] } else { Warn "$($m[0]) failed - run 'ollama pull $($m[0])' later" }
}

# ---------- 3. Python + Open WebUI (chat app) ----------
function Find-Python311 {
    $p = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (Test-Path $p) { return $p }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $p = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $p) { return $p.Trim() }
    }
    return $null
}
$py = Find-Python311
if (-not $py) { Winget-Install 'Python.Python.3.11' 'Python 3.11'; $py = Find-Python311 }

$venv = Join-Path $Root 'openwebui'
$webui = Join-Path $venv 'Scripts\open-webui.exe'
if ($py) {
    if (-not (Test-Path $webui)) {
        Say 'Installing Open WebUI (takes a few minutes)'
        & $py -m venv $venv
        & (Join-Path $venv 'Scripts\python.exe') -m pip install --upgrade pip
        & (Join-Path $venv 'Scripts\python.exe') -m pip install open-webui
    }
    if (Test-Path $webui) { Ok 'Open WebUI installed' } else { Warn 'Open WebUI did not install' }
} else {
    Warn 'Python 3.11 not found - skipped Open WebUI. Install Python 3.11 and run this again.'
}

# ---------- 4. Start script + desktop shortcut ----------
Say 'Creating the "Start Local AI" shortcut'
$startBat = Join-Path $Root 'Start-LocalAI.bat'
@"
@echo off
title Local AI
echo Starting Local AI... keep this window open while you use it.
curl -s http://127.0.0.1:11434/api/version >nul 2>&1 || start "" /min "$ollama" serve
set OLLAMA_BASE_URL=http://127.0.0.1:11434
set DATA_DIR=$Root\webui-data
set ENABLE_OPENAI_API=False
start "" cmd /c "timeout /t 15 >nul && start http://localhost:8080"
"$webui" serve --port 8080
"@ | Set-Content -Path $startBat -Encoding ASCII

$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $desktop 'Start Local AI.lnk'))
$lnk.TargetPath = $startBat
$lnk.WorkingDirectory = $Root
$lnk.Save()
Ok 'Desktop shortcut "Start Local AI" created'

# ---------- 5. VS Code + Continue (coding helper) ----------
if (-not (Get-Command code -ErrorAction SilentlyContinue)) { Winget-Install 'Microsoft.VisualStudioCode' 'VS Code' }
$code = Get-Command code -ErrorAction SilentlyContinue
if (-not $code) {
    $c = Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd'
    if (Test-Path $c) { $code = $c }
} else { $code = $code.Source }
if ($code) {
    Say 'Installing the Continue extension in VS Code'
    & $code --install-extension Continue.continue --force
    $contDir = Join-Path $env:USERPROFILE '.continue'
    $contCfg = Join-Path $contDir 'config.yaml'
    if (-not (Test-Path $contCfg)) {
        New-Item -ItemType Directory -Force -Path $contDir | Out-Null
        @"
name: Local AI
version: 1.0.0
schema: v1
models:
  - name: Qwen2.5-Coder 14B
    provider: ollama
    model: qwen2.5-coder:14b
    roles: [chat, edit, apply]
  - name: Qwen3 30B
    provider: ollama
    model: qwen3:30b
    roles: [chat]
  - name: Qwen2.5-Coder 1.5B
    provider: ollama
    model: qwen2.5-coder:1.5b
    roles: [autocomplete]
  - name: Nomic Embed
    provider: ollama
    model: nomic-embed-text
    roles: [embed]
"@ | Set-Content -Path $contCfg -Encoding UTF8
        Ok 'Continue set up to use your local models'
    } else { Ok 'Continue already has a config - left it as is' }
} else { Warn 'VS Code not found - skipped the coding helper' }

# ---------- Done ----------
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host ' DONE! Double-click "Start Local AI" on your desktop.' -ForegroundColor Green
Write-Host ' Your browser opens http://localhost:8080 - create an account' -ForegroundColor Green
Write-Host ' (it stays on your PC), pick a model at the top, and chat.' -ForegroundColor Green
Write-Host ' Coding: open VS Code and click the Continue icon on the left.' -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Green
