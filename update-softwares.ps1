$ErrorActionPreference = "Stop"
function Test-Command {
    param (
        [string]$command
    )
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        Write-Host "Please install $command"
        exit 1
    }
}


Test-Command git
Test-Command python3

# $env:ISSUE_NUMBER が定義されていない場合は、スクリプトを終了
if (-not $env:ISSUE_NUMBER) {
    Write-Host "ISSUE_NUMBER is not defined. Exiting script."
    exit 1
}

$userFolder = [System.Environment]::GetFolderPath('UserProfile')
$projectPath = Join-Path $userFolder "update-softwares"

New-Item -ItemType Directory -Force -Path $projectPath | Out-Null
Set-Location -Path $projectPath -ErrorAction Stop

# clone repository
if (-not (Test-Path "$projectPath\.git")) {
    git clone https://github.com/book000/update-softwares.git .
}
else {
    git pull
}

python -m src $env:ISSUE_NUMBER
