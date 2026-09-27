param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3
$source = [IO.Path]::GetFullPath($ReleaseRoot).TrimEnd('\')
$files = @('AI Location Finder.pyw', 'assets/world_map.png', 'Installer.bat', 'LICENSE', 'location_map.py', 'location_prompts.py', 'location_providers.py', 'READ ME.txt', 'screen_capture.py')
$base = Join-Path ([IO.Path]::GetTempPath()) ('f' + [Guid]::NewGuid().ToString('N').Substring(0, 6))
if ($base.Length -gt 60) { throw "The test fixture root is too long: $base" }
[IO.Directory]::CreateDirectory($base) | Out-Null

function New-Fixture([string]$Name, [string[]]$Omit = @()) {
    $target = Join-Path $base $Name
    [IO.Directory]::CreateDirectory($target) | Out-Null
    foreach ($relative in $files) {
        if ($relative -in $Omit) { continue }
        $from = Join-Path $source ($relative.Replace('/', '\'))
        if (-not [IO.File]::Exists($from)) { throw "Missing release input: $relative" }
        $to = Join-Path $target ($relative.Replace('/', '\'))
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($to)) | Out-Null
        [IO.File]::Copy($from, $to)
    }
    return $target
}

function Assert-EarlyFailure([string]$Folder, [string]$Expected) {
    Push-Location -LiteralPath $Folder
    try {
        $output = (& $env:ComSpec /d /c 'call "Installer.bat" --yes --no-pause' 2>&1 | Out-String)
        $code = $LASTEXITCODE
    } finally { Pop-Location }
    if ($code -eq 0) { throw "Setup unexpectedly passed in $Folder" }
    if ($output -notmatch [regex]::Escape($Expected)) { throw "Missing expected error '$Expected' in $Folder`n$output" }
    if ($output -notmatch 'How to fix it:') { throw "Missing repair guidance in $Folder`n$output" }
    if ($output -match 'Downloading and preparing private Python') { throw "Setup downloaded Python before rejecting $Folder" }
    $log = Join-Path $Folder 'setup.log'
    if ([IO.File]::Exists($log) -and [IO.File]::ReadAllText($log) -notmatch 'HOW TO FIX:') {
        throw "Repair guidance was not logged in $Folder"
    }
}

$missing = New-Fixture 'a b' @('AI Location Finder.pyw')
Assert-EarlyFailure $missing 'AI Location Finder.pyw is missing'
$invalid = New-Fixture 'c d'
[IO.File]::WriteAllBytes((Join-Path $invalid 'AI Location Finder.pyw'), [byte[]](0xFF, 0xFE))
Assert-EarlyFailure $invalid 'An app source file or the offline map is unreadable'
$invalidMap = New-Fixture 'e f'
[IO.File]::WriteAllBytes((Join-Path $invalidMap 'assets\world_map.png'), [byte[]](1, 2, 3, 4, 5, 6, 7, 8, 9))
Assert-EarlyFailure $invalidMap 'An app source file or the offline map is unreadable'
$unsafeShortcut = New-Fixture 'g h'
[IO.Directory]::CreateDirectory((Join-Path $unsafeShortcut 'AI Location Finder.lnk')) | Out-Null
Assert-EarlyFailure $unsafeShortcut 'shortcut is unsafe'
$longPath = Join-Path $base ('x' * 70)
if ($longPath.Length -le 72) { throw 'The long-path fixture did not exceed the limit.' }
$longFixture = New-Fixture ('x' * 70)
Assert-EarlyFailure $longFixture '72 characters or fewer'
$missingLicense = New-Fixture 'i j' @('LICENSE')
Assert-EarlyFailure $missingLicense 'bundled Tool License is missing'
$unsupportedArch = New-Fixture 'k l'
$priorArch = $env:PROCESSOR_ARCHITECTURE
$priorWowArch = $env:PROCESSOR_ARCHITEW6432
try {
    $env:PROCESSOR_ARCHITECTURE = 'x86'
    Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue
    Assert-EarlyFailure $unsupportedArch 'supports 64-bit and ARM64 Windows only'
} finally {
    $env:PROCESSOR_ARCHITECTURE = $priorArch
    if ($priorWowArch) { $env:PROCESSOR_ARCHITEW6432 = $priorWowArch }
}
Write-Host 'AI Location Finder negative preflight cases passed before Python download, including paths with spaces, overlong paths, and unsupported architecture.'
exit 0
