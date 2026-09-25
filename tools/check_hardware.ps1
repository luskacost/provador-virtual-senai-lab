# Provador Virtual 3D - verificacao de hardware (Windows)
# Gera docs/hardware_raw.txt com GPU, webcam, CPU/RAM e versoes do Python.
$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $PSScriptRoot
$out  = Join-Path $root "docs\hardware_raw.txt"
$lines = New-Object System.Collections.Generic.List[string]
function Add($s) { $lines.Add([string]$s) }

Add "# Hardware check - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
$os = Get-CimInstance Win32_OperatingSystem
Add "OS: $($os.Caption) $($os.Version) ($($os.OSArchitecture))"
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
Add "CPU: $($cpu.Name.Trim()) | cores=$($cpu.NumberOfCores) threads=$($cpu.NumberOfLogicalProcessors)"
Add ("RAM: {0:N1} GB" -f ($os.TotalVisibleMemorySize / 1MB))

Add ""; Add "## GPUs (Win32_VideoController)"
Get-CimInstance Win32_VideoController | ForEach-Object {
  Add "- $($_.Name) | driver=$($_.DriverVersion) | status=$($_.Status)"
}
Add ""; Add "## nvidia-smi"
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) {
  (& nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader 2>&1) | ForEach-Object { Add "- $_" }
} else { Add "- nvidia-smi nao encontrado" }

Add ""; Add "## Cameras (PnP Camera/Image)"
$cams = Get-PnpDevice -PresentOnly | Where-Object { $_.Class -in @("Camera","Image") }
if ($cams) { $cams | ForEach-Object { Add "- $($_.FriendlyName) | class=$($_.Class) | status=$($_.Status)" } }
else { Add "- nenhuma webcam detectada" }

Add ""; Add "## Python"
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) { Add "py launcher: $($py.Source)"; (& py -0p 2>&1) | ForEach-Object { Add "  $_" } }
else { Add "py launcher: nao encontrado" }
Get-Command python -All -ErrorAction SilentlyContinue | ForEach-Object {
  $v = (& $_.Source --version 2>&1)
  Add "python: $($_.Source) -> $v"
}
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) { Add "uv: $(& uv --version 2>&1)"; (& uv python list --only-installed 2>&1) | ForEach-Object { Add "  $_" } }
else { Add "uv: nao encontrado" }
$wg = Get-Command winget -ErrorAction SilentlyContinue
Add ("winget: " + $(if ($wg) { "disponivel" } else { "nao encontrado" }))

$lines | Out-File -FilePath $out -Encoding utf8
Write-Host ($lines -join "`n")
Write-Host "`nSalvo em $out"
