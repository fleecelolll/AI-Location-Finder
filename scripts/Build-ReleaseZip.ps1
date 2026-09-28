param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3

$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$output = [IO.Path]::GetFullPath($OutputPath)

function Read-TrackedBlob([string]$RelativePath) {
    $start = [Diagnostics.ProcessStartInfo]::new('git')
    $start.WorkingDirectory = $root
    $start.ArgumentList.Add('cat-file')
    $start.ArgumentList.Add('blob')
    $start.ArgumentList.Add("HEAD:$RelativePath")
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = [Diagnostics.Process]::Start($start)
    try {
        $buffer = [IO.MemoryStream]::new()
        try {
            $process.StandardOutput.BaseStream.CopyTo($buffer)
            $process.WaitForExit()
            if ($process.ExitCode -ne 0) {
                throw ('Could not read committed release input {0}: {1}' -f $RelativePath, $process.StandardError.ReadToEnd())
            }
            return ,$buffer.ToArray()
        } finally { $buffer.Dispose() }
    } finally { $process.Dispose() }
}

$outputDirectory = [IO.Path]::GetDirectoryName($output)
if (-not [IO.Directory]::Exists($outputDirectory)) {
    throw "Output directory does not exist: $outputDirectory"
}
if ([IO.File]::Exists($output) -or [IO.Directory]::Exists($output)) {
    throw "Refusing to overwrite an existing release archive: $output"
}

Push-Location -LiteralPath $root
try {
    $dirty = @(& git status --porcelain --untracked-files=normal)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0) {
        throw 'The release source tree must be clean before packaging.'
    }
    $commit = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the release commit.' }

    $versionMatch = [regex]::Match([Text.Encoding]::UTF8.GetString((Read-TrackedBlob 'AI Location Finder.pyw')), '(?m)^APP_VERSION = "(?<version>\d+\.\d+\.\d+)"\s*$')
    if (-not $versionMatch.Success) { throw 'The app has no unambiguous release version.' }
    $version = $versionMatch.Groups['version'].Value
    $installerText = [Text.Encoding]::UTF8.GetString((Read-TrackedBlob 'Installer.bat'))
    $installerVersion = [regex]::Match($installerText, '\$data\.version -cne ''(?<version>\d+\.\d+\.\d+)''')
    if (-not $installerVersion.Success -or $installerVersion.Groups['version'].Value -cne $version) {
        throw 'The installer final-check version must match the committed app version.'
    }
    if ([IO.Path]::GetFileName($output) -cne "AI-Location-Finder-v$version.zip") {
        throw "The archive filename must be AI-Location-Finder-v$version.zip."
    }

    $fixed = @('AI Location Finder.pyw', 'assets/world_map.png', 'Installer.bat', 'LICENSE', 'location_map.py', 'location_prompts.py', 'location_providers.py', 'READ ME.txt', 'screen_capture.py', 'requirements-win-arm64.txt', 'requirements-win-x64.txt')
    $paths = @($fixed | Sort-Object -CaseSensitive)
    if ($paths.Count -ne 11 -or (@($paths | Select-Object -Unique)).Count -ne 11) {
        throw 'The release file list is incomplete or contains duplicates.'
    }
    $committed = @{}
    foreach ($relative in $paths) {
        $path = Join-Path $root ($relative.Replace('/', '\'))
        $item = Get-Item -LiteralPath $path -Force
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.Length -lt 1) {
            throw "Release input is missing, empty, or unsafe: $relative"
        }
        $blob = [byte[]](Read-TrackedBlob $relative)
        if ($relative -eq 'Installer.bat') {
            # Git stores LF, while .gitattributes requires a Windows CRLF batch file.
            # Make that conversion explicit so different checkout settings cannot alter the ZIP.
            $batchText = [Text.UTF8Encoding]::new($false, $true).GetString($blob)
            if ($batchText.Contains([char]13)) { throw 'The committed installer batch file has unexpected CR bytes.' }
            $blob = [Text.UTF8Encoding]::new($false).GetBytes(
                $batchText.Replace([string][char]10, ([string][char]13 + [string][char]10))
            )
        }
        if ($blob.Length -lt 1) { throw "Committed release input is empty: $relative" }
        $committed[$relative] = $blob
    }

    Add-Type -AssemblyName System.IO.Compression
    $stamp = [DateTimeOffset]::Parse('2026-09-27T10:00:00+00:00')
    $stream = [IO.File]::Open($output, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $archive = [IO.Compression.ZipArchive]::new($stream, [IO.Compression.ZipArchiveMode]::Create, $true)
        try {
            foreach ($relative in $paths) {
                $entry = $archive.CreateEntry($relative, [IO.Compression.CompressionLevel]::Optimal)
                $entry.LastWriteTime = $stamp
                $target = $entry.Open()
                try {
                    $bytes = [byte[]]$committed[$relative]
                    $target.Write($bytes, 0, $bytes.Length)
                } finally { $target.Dispose() }
            }
        } finally { $archive.Dispose() }
    } finally { $stream.Dispose() }

    $check = [IO.Compression.ZipFile]::OpenRead($output)
    try {
        $actual = @($check.Entries | ForEach-Object FullName)
        if ($actual.Count -ne $paths.Count -or (Compare-Object $paths $actual)) {
            throw 'The completed archive entry list does not match the release file list.'
        }
        foreach ($entry in $check.Entries) {
            $sourceHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([byte[]]$committed[$entry.FullName]))
            $entryStream = $entry.Open()
            try {
                $sha = [Security.Cryptography.SHA256]::Create()
                try { $entryHash = [Convert]::ToHexString($sha.ComputeHash($entryStream)) }
                finally { $sha.Dispose() }
            } finally { $entryStream.Dispose() }
            if ($entryHash -cne $sourceHash) { throw "Archive content mismatch: $($entry.FullName)" }
        }
    } finally { $check.Dispose() }

    $hash = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
    $size = (Get-Item -LiteralPath $output).Length
    Write-Host "Release commit: $commit"
    Write-Host "Release version: $version"
    Write-Host "Archive files: $($paths.Count)"
    Write-Host "Archive bytes: $size"
    Write-Host "Archive SHA-256: $hash"
    Write-Host "Archive path: $output"
} finally {
    Pop-Location
}
