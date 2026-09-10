# Restart AmiBroker into a known-clean state.
#
# Between test refs this is NOT optional: AmiBroker caches compiled AFL and its
# includes, so a second run against changed include files can silently execute
# the first run's code.
#
# AmiBroker location: set SD_AMIBROKER_HOME if yours is elsewhere.
$ErrorActionPreference = 'Continue'
$install = if ($env:SD_AMIBROKER_HOME) { $env:SD_AMIBROKER_HOME } else { 'C:\Program Files\AmiBroker' }
if (-not (Test-Path (Join-Path $install 'Broker.exe'))) {
    Write-Host "No Broker.exe under [$install]. Set SD_AMIBROKER_HOME to your AmiBroker folder."
    exit 2
}

Get-Process Broker -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host ("killing Broker pid=" + $_.Id)
    $_ | Stop-Process -Force
}
Start-Sleep -Seconds 3

# Working directory MUST be the install dir: AmiBroker resolves Formulas\...
# relative to CWD, and launching from elsewhere makes every chart error out.
$p = Start-Process -FilePath (Join-Path $install 'Broker.exe') -WorkingDirectory $install -PassThru
Write-Host ("started pid=" + $p.Id)

$deadline = (Get-Date).AddSeconds(60)
do {
    Start-Sleep -Seconds 2
    $proc = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
    $title = if ($proc) { $proc.MainWindowTitle } else { $null }
} while ((Get-Date) -lt $deadline -and [string]::IsNullOrEmpty($title))

Write-Host ("MainWindowTitle=[" + $title + "]")
