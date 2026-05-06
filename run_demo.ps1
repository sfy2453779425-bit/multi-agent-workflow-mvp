$ErrorActionPreference = "Stop"
$BundledPython = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (Test-Path $BundledPython) {
    $Python = $BundledPython
} else {
    $Python = "python"
}

& $Python "$PSScriptRoot\demo.py" "서울 내일 날씨 알려주고 옷 추천해줘"
