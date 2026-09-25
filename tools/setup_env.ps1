# Provador Virtual 3D - cria o .venv com Python 3.11/3.12, instala dependencias, baixa modelos e roda o check.
# Uso (na raiz do projeto):  powershell -ExecutionPolicy Bypass -File tools\setup_env.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

function Test-PyLauncher($ver) {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if (-not $py) { return $false }
  & py "-$ver" -c "import sys" 2>$null
  return ($LASTEXITCODE -eq 0)
}

if (Test-Path $venvPy) {
  $v = & $venvPy -c "import sys;print('%d.%d'%sys.version_info[:2])"
  if ($v -notin @("3.11","3.12")) {
    Write-Host ".venv existente usa Python $v (incompativel). Removendo..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force (Join-Path $root ".venv")
  }
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not (Test-Path $venvPy)) {
  if ($uv) {
    Write-Host "Criando .venv com uv (Python 3.11)..." -ForegroundColor Cyan
    & uv venv --python 3.11 .venv
  } elseif (Test-PyLauncher "3.11") {
    Write-Host "Criando .venv com py -3.11..." -ForegroundColor Cyan
    & py -3.11 -m venv .venv
  } elseif (Test-PyLauncher "3.12") {
    Write-Host "Criando .venv com py -3.12..." -ForegroundColor Cyan
    & py -3.12 -m venv .venv
  } else {
    Write-Host "Python 3.11/3.12 nao encontrado." -ForegroundColor Red
    Write-Host "Instale uma das opcoes e rode este script de novo:"
    Write-Host "  winget install -e --id astral-sh.uv          (recomendado: o uv baixa o Python sozinho)"
    Write-Host "  winget install -e --id Python.Python.3.11"
    exit 1
  }
}

Write-Host "Instalando dependencias..." -ForegroundColor Cyan
if ($uv) {
  & uv pip install --python $venvPy -r requirements-dev.txt
  & uv pip install --python $venvPy -e .
} else {
  & $venvPy -m pip install --upgrade pip
  & $venvPy -m pip install -r requirements-dev.txt
  & $venvPy -m pip install -e .
}

Write-Host "Baixando modelos do MediaPipe..." -ForegroundColor Cyan
& $venvPy tools\download_models.py

Write-Host "`nVerificacao do ambiente:" -ForegroundColor Cyan
& $venvPy -m provador.check --camera
