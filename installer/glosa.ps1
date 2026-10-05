# glosa launcher for Windows: start, stop, update or remove the containers.
# Used by the Start menu and desktop shortcuts the installer creates.
param(
    [ValidateSet("start", "stop", "update", "uninstall")] [string]$Action = "start",
    [switch]$RemoveData,
    [switch]$Quiet,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$Compose = Join-Path $Here "compose.yaml"
$EnvFile = Join-Path $Here ".env"
$Port = 7878
if (Test-Path $EnvFile) {
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^GLOSA_PORT=(\d+)" } | Select-Object -First 1
    if ($line) { $Port = [int]($line -replace "^GLOSA_PORT=", "") }
}
$Project = if ($env:GLOSA_PROJECT) { $env:GLOSA_PROJECT } else { "glosa" }  # another name only for testing
$Url = "http://localhost:$Port"
$Es = (Get-UICulture).TwoLetterISOLanguageName -eq "es"

function Say([string]$es, [string]$en) {
    if (-not $Quiet) { if ($Es) { Write-Host $es } else { Write-Host $en } }
}

function Fail([string]$es, [string]$en) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($(if ($Es) { $es } else { $en }), "glosa") | Out-Null
    exit 1
}

function Compose([string[]]$Arguments) {
    & docker compose -p $Project -f $Compose --env-file $EnvFile @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($Arguments -join ' ') failed" }
}

function Wait-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Fail "Docker Desktop no está instalado. Vuelve a ejecutar el instalador de glosa." "Docker Desktop is not installed. Run the glosa installer again."
    }
    & docker info *> $null
    if ($LASTEXITCODE -eq 0) { return }
    Say "Abriendo Docker Desktop…" "Starting Docker Desktop…"
    $desktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Test-Path $desktop) { Start-Process $desktop }
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Seconds 2
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) { return }
    }
    Fail "Docker Desktop no terminó de arrancar. Ábrelo a mano, espera a que diga que está en marcha y vuelve a abrir glosa." "Docker Desktop did not finish starting. Open it yourself, wait until it says it is running, then open glosa again."
}

function Wait-App {
    for ($i = 0; $i -lt 90; $i++) {
        try {
            $r = Invoke-WebRequest "$Url/api/health" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Seconds 2
    }
    Fail "glosa no respondió a tiempo. Prueba a abrirla otra vez." "glosa did not answer in time. Try opening it again."
}

switch ($Action) {
    "start" {
        Wait-Docker
        $firstRun = -not (Test-Path (Join-Path $Here ".started"))
        if ($firstRun) {
            Say "Descargando glosa (solo la primera vez)…" "Downloading glosa (first time only)…"
            Compose @("pull")
        }
        Say "Arrancando glosa…" "Starting glosa…"
        Compose @("up", "-d")
        Wait-App
        if ($firstRun) {
            # The extras chosen in the installer download in the background; the Extras page shows progress.
            $preset = Join-Path $Here "preset.txt"
            if (Test-Path $preset) {
                $name = (Get-Content $preset -Raw).Trim()
                if ($name -in @("light", "recommended")) {
                    try { Invoke-RestMethod -Method Post "$Url/api/extras-preset/$name" | Out-Null } catch { }
                }
            }
            Set-Content (Join-Path $Here ".started") (Get-Date -Format o)
            if (-not $NoBrowser) { Start-Process "$Url/extras" }
        } elseif (-not $NoBrowser) {
            Start-Process $Url
        }
    }
    "stop" {
        Wait-Docker
        Compose @("stop")
        Say "glosa se detuvo." "glosa stopped."
    }
    "update" {
        Wait-Docker
        Say "Buscando la última versión…" "Getting the latest version…"
        Compose @("pull")
        Compose @("up", "-d")
        Wait-App
        if (-not $NoBrowser) { Start-Process $Url }
    }
    "uninstall" {
        & docker info *> $null
        if ($LASTEXITCODE -ne 0) { return }  # nothing to remove without Docker
        $down = @("down")
        if ($RemoveData) { $down += "--volumes" }
        try { Compose $down } catch { }
        # The extras the app installed: only containers it labelled as its own.
        $extraImages = & docker ps -a --filter "label=glosa.extra" --format "{{.Image}}"
        $extras = & docker ps -aq --filter "label=glosa.extra"
        if ($extras) { & docker rm -f $extras *> $null }
        if ($extraImages) { & docker rmi ($extraImages | Sort-Object -Unique) *> $null }
        if ($RemoveData) {
            foreach ($v in @("glosa-ollama", "glosa-translator-models", "glosa-tts-supertonic-cache")) {
                & docker volume rm $v *> $null
            }
        }
        $images = & docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -like "ghcr.io/cokefish/glosa-*" }
        if ($images) { & docker rmi $images *> $null }
    }
}
