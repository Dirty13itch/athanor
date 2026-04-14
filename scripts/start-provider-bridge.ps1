param(
    [string]$Token,
    [int]$Port = 9011,
    [string]$WorkspaceDir = "C:\Athanor",
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Athanor"
$projectRoot = Join-Path $repoRoot "projects\agents"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$appDir = Join-Path $projectRoot "src"
$logDir = Join-Path $repoRoot "tmp\provider-bridge"
$stdoutLog = Join-Path $logDir "provider-bridge.stdout.log"
$stderrLog = Join-Path $logDir "provider-bridge.stderr.log"
$healthUrl = "http://127.0.0.1:$Port/health"

if (-not (Test-Path $pythonExe)) {
    throw "Missing Python executable at $pythonExe"
}

if (-not $Token) {
    throw "A provider bridge token is required."
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$existing = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -ieq "python.exe" -or $_.Name -ieq "pythonw.exe") -and
        $_.CommandLine -like "*athanor_agents.provider_bridge_server:app*" -and
        $_.CommandLine -like "*--port $Port*"
    }

if ($existing -and -not $Restart) {
    Write-Output "Provider bridge already running on port $Port."
    $existing | Select-Object ProcessId, CommandLine
    try {
        $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 $healthUrl
        Write-Output $response.Content
    } catch {
        Write-Warning "Existing process found, but health probe failed: $($_.Exception.Message)"
    }
    exit 0
}

if ($existing -and $Restart) {
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Seconds 1
}

$previousToken = $env:ATHANOR_PROVIDER_BRIDGE_TOKEN
$previousWorkspace = $env:ATHANOR_PROVIDER_WORKSPACE_DIR

try {
    $env:ATHANOR_PROVIDER_BRIDGE_TOKEN = $Token
    $env:ATHANOR_PROVIDER_WORKSPACE_DIR = $WorkspaceDir

    $process = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList @(
            "-m",
            "uvicorn",
            "athanor_agents.provider_bridge_server:app",
            "--host",
            "0.0.0.0",
            "--port",
            "$Port",
            "--app-dir",
            $appDir
        ) `
        -WorkingDirectory $projectRoot `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
} finally {
    $env:ATHANOR_PROVIDER_BRIDGE_TOKEN = $previousToken
    $env:ATHANOR_PROVIDER_WORKSPACE_DIR = $previousWorkspace
}

for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 $healthUrl
        if ($response.StatusCode -eq 200) {
            Write-Output "Provider bridge started on port $Port (PID $($process.Id))."
            Write-Output $response.Content
            exit 0
        }
    } catch {
        if ($process.HasExited) {
            break
        }
    }
}

if (-not $process.HasExited) {
    Write-Warning "Provider bridge process started (PID $($process.Id)) but health did not become ready in time."
    exit 0
}

$stderr = ""
if (Test-Path $stderrLog) {
    $stderr = Get-Content -Path $stderrLog -Raw
}
throw "Provider bridge failed to start. stderr:`n$stderr"
