param(
    [int]$Port = 8000,
    [switch]$NoBrowser,
    [switch]$Status,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$ProjectDir = $PSScriptRoot
$App = Join-Path $ProjectDir "web_app.py"
$PidFile = Join-Path $ProjectDir ".demo_server.pid"
$UrlFile = Join-Path $ProjectDir ".demo_server.url"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (Test-Path $BundledPython) {
    $Python = $BundledPython
} else {
    $Python = "python"
}

function Get-DemoProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -like "*web_app.py*" -and
            $_.CommandLine -like "*$ProjectDir*"
        }
}

function Test-PortOpen {
    param([int]$CheckPort)
    try {
        $client = New-Object Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $CheckPort, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(200, $false)
        if ($connected) {
            $client.EndConnect($async)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

function Test-DemoUrl {
    param([int]$CheckPort)
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$CheckPort/?lang=zh" -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -eq 200 -and $response.Content -like "*Workflow*")
    } catch {
        return $false
    }
}

function Get-DemoPort {
    param($ProcessItem)
    $match = [regex]::Match($ProcessItem.CommandLine, "web_app\.py\s+(\d+)")
    if ($match.Success) {
        return [int]$match.Groups[1].Value
    }
    return 8000
}

function Stop-DemoServer {
    $items = Get-DemoProcesses
    foreach ($item in $items) {
        Stop-Process -Id $item.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped demo server PID $($item.ProcessId)"
    }
    Remove-Item $PidFile, $UrlFile -ErrorAction SilentlyContinue
}

function Write-DemoStatus {
    $items = @(Get-DemoProcesses)
    foreach ($item in $items) {
        $runningPort = Get-DemoPort -ProcessItem $item
        if (Test-DemoUrl -CheckPort $runningPort) {
            Write-Host "Demo server is running."
            Write-Host "PID: $($item.ProcessId)"
            Write-Host "URL: http://127.0.0.1:$runningPort/?lang=zh"
            return
        }
    }
    Write-Host "Demo server is not running."
}

if ($Stop) {
    Stop-DemoServer
    exit 0
}

if ($Status) {
    Write-DemoStatus
    exit 0
}

# Start from a clean project-local demo process to avoid stale code or dead ports.
Stop-DemoServer | Out-Null

while (Test-PortOpen -CheckPort $Port) {
    $Port += 1
}

$Url = "http://127.0.0.1:$Port/?lang=zh"
$process = Start-Process -FilePath $Python `
    -ArgumentList @($App, $Port) `
    -WorkingDirectory $ProjectDir `
    -PassThru `
    -WindowStyle Hidden

$ready = $false
for ($i = 0; $i -lt 30; $i += 1) {
    Start-Sleep -Milliseconds 300
    if (Test-DemoUrl -CheckPort $Port) {
        $ready = $true
        break
    }
    if ($process.HasExited) {
        throw "Web demo failed to start. Run python web_app.py to inspect the error."
    }
}

if (-not $ready) {
    throw "Web demo did not respond on $Url"
}

Set-Content -Path $PidFile -Value $process.Id -Encoding ascii
Set-Content -Path $UrlFile -Value $Url -Encoding ascii

if (-not $NoBrowser) {
    Start-Process $Url
}

Write-Host ""
Write-Host "Demo is running:"
Write-Host $Url
Write-Host ""
Write-Host "Status: powershell -File run_web.ps1 -Status"
Write-Host "Stop:   powershell -File run_web.ps1 -Stop"
Write-Host ""
Write-Host "You can close this window. The local server will keep running in the background."
Start-Sleep -Seconds 3
