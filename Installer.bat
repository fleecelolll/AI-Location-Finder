@echo off
setlocal EnableExtensions DisableDelayedExpansion
title AI Location Finder Setup
set "INSTALLER_SELF=%~f0"
set "INSTALLER_ROOT=%~dp0"

set "NO_PAUSE=0"
set "ASSUME_YES=0"
set "SETUP_CHILD=0"
set "LOG_READY="
set "DIAGNOSTIC_LOG=nul"
set "PATHS_VALIDATED="

:ParseArguments
if "%~1"=="" goto ArgumentsReady
if /I "%~1"=="--no-pause" goto ParseNoPause
if /I "%~1"=="--yes" goto ParseYes
if /I "%~1"=="--fleece-setup-child" goto ParseChildMarker
goto UnknownOption

:ParseChildMarker
if /I not "%FLEECE_LOCATION_INSTALLER_CHILD%"=="1" goto UnknownOption
set "SETUP_CHILD=1"
shift
goto ParseArguments

:UnknownOption
echo.
echo   Unknown setup option. No setup changes were made.
echo   Supported options: --yes --no-pause
echo.
exit /b 2

:ParseNoPause
set "NO_PAUSE=1"
shift
goto ParseArguments

:ParseYes
set "ASSUME_YES=1"
shift
goto ParseArguments

:ArgumentsReady
if "%SETUP_CHILD%"=="1" goto DedicatedChildReady
set "SETUP_CHILD_ARGS=--fleece-setup-child"
if "%ASSUME_YES%"=="1" set "SETUP_CHILD_ARGS=%SETUP_CHILD_ARGS% --yes"
if "%NO_PAUSE%"=="1" set "SETUP_CHILD_ARGS=%SETUP_CHILD_ARGS% --no-pause"
set "FLEECE_LOCATION_INSTALLER_CHILD=1"
"%SystemRoot%\System32\cmd.exe" /d /c call "%INSTALLER_SELF%" %SETUP_CHILD_ARGS%
exit /b %ERRORLEVEL%

:DedicatedChildReady
set "FLEECE_LOCATION_INSTALLER_CHILD="

set "ROOT=%INSTALLER_ROOT%"
set "MAX_ROOT_LENGTH=72"
set "APP_FILE=%ROOT%AI Location Finder.pyw"
set "PROVIDERS_FILE=%ROOT%location_providers.py"
set "MAP_MODULE=%ROOT%location_map.py"
set "PROMPTS_FILE=%ROOT%location_prompts.py"
set "CAPTURE_FILE=%ROOT%screen_capture.py"
set "MAP_ASSET=%ROOT%assets\world_map.png"
set "LOG=%ROOT%setup.log"
set "RUNTIME=%ROOT%.runtime"
set "SETUP_LOCK=%RUNTIME%\setup.lock"
set "SETUP_LOCK_OWNER=%SETUP_LOCK%\owner.json"
set "SETUP_MARKER=%RUNTIME%\setup-complete.txt"
set "SETUP_LOCK_HELD=0"
set "SETUP_LOCK_TOKEN="
set "SETUP_LOCK_MAX_AGE_MINUTES=180"
set "DOWNLOADS=%RUNTIME%\downloads"
set "PYTHON_DIR=%RUNTIME%\python"
set "RUNTIME_PY=%PYTHON_DIR%\python.exe"
set "RUNTIME_PYW=%PYTHON_DIR%\pythonw.exe"
set "LOCAL_SITE=%PYTHON_DIR%\Lib\site-packages"
set "PIP_WHEEL=%PYTHON_DIR%\pip.whl"
set "VENV=%ROOT%.venv"
set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "CURL_EXE=%SystemRoot%\System32\curl.exe"
set "ROBOCOPY_EXE=%SystemRoot%\System32\robocopy.exe"
set "PYTHON_VERSION=3.14.7"
set "PYSIDE_VERSION=6.11.2"
set "PYSIDE_DISTRIBUTION=PySide6-Essentials"
set "HTTPX_VERSION=0.28.1"
set "ANYIO_VERSION=4.15.1"
set "CERTIFI_VERSION=2026.7.22"
set "H11_VERSION=0.16.0"
set "HTTPCORE_VERSION=1.0.9"
set "IDNA_VERSION=3.19"
set "SHIBOKEN_VERSION=6.11.2"
set "TYPING_EXTENSIONS_VERSION=4.16.0"
set "PYTHON_PACKAGES=%PYSIDE_DISTRIBUTION%==%PYSIDE_VERSION% shiboken6==%SHIBOKEN_VERSION% httpx==%HTTPX_VERSION% httpcore==%HTTPCORE_VERSION% h11==%H11_VERSION% certifi==%CERTIFI_VERSION% anyio==%ANYIO_VERSION% idna==%IDNA_VERSION% typing-extensions==%TYPING_EXTENSIONS_VERSION%"
set "PYPI_INDEX=https://pypi.org/simple"
set "PIP_WHEEL_URL=https://files.pythonhosted.org/packages/f3/6e/1736e5b4ae2b778ef2f81c47d797de9f891d4d8acb047a24ca37a60294dd/pip-26.2.1-py3-none-any.whl"
set "PIP_WHEEL_SHA256=71138ADF1F4CA900CDB7D289C21B7494329F2332B6D85F0E1C42108C0384ED3E"

set "NATIVE_ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "NATIVE_ARCH=%PROCESSOR_ARCHITEW6432%"
if /I "%NATIVE_ARCH%"=="AMD64" goto ArchitectureX64
if /I "%NATIVE_ARCH%"=="ARM64" goto ArchitectureArm64
set "FAIL_MESSAGE=This installer currently supports 64-bit and ARM64 Windows only."
goto Failed

:ArchitectureX64
set "ARCH=x64"
set "PYTHON_URL=https://www.python.org/ftp/python/3.14.7/python-3.14.7-embed-amd64.zip"
set "PYTHON_SHA256=D297E5FF019966817AD8502465176139F2D3D840FA4ED84B13BED399A6AB1F15"
goto ArchitectureReady

:ArchitectureArm64
set "ARCH=arm64"
set "PYTHON_URL=https://www.python.org/ftp/python/3.14.7/python-3.14.7-embed-arm64.zip"
set "PYTHON_SHA256=F6773983C8959D4281E48C4540CB0BDD23E42391E4E951CE17E7CEB52658F21C"

:ArchitectureReady
if not exist "%POWERSHELL_EXE%" (
    set "FAIL_MESSAGE=Trusted Windows PowerShell is missing from the system folder."
    goto Failed
)
if not exist "%ROBOCOPY_EXE%" (
    set "FAIL_MESSAGE=Trusted Windows file-copy support is missing from the system folder."
    goto Failed
)
if not exist "%ROOT%LICENSE" (
    set "FAIL_MESSAGE=The bundled Tool License is missing from this folder. Extract a fresh official release and try again."
    goto Failed
)
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "if([IO.Path]::GetFullPath($env:ROOT).Length -gt [int]$env:MAX_ROOT_LENGTH){exit 2}" >nul 2>nul
if errorlevel 1 (
    set "FAIL_MESSAGE=The complete app folder path must be 72 characters or fewer. Move the extracted folder closer to the drive root and try again."
    goto Failed
)
cls
echo.
echo   The app and private components stay inside this folder.
echo   The folder-local shortcut opens the private Python directly.
echo   Setup does not need administrator access.
echo.
echo      Python environment     runs the app
echo      PySide6                the app window and detailed map
echo      Map layers             street, satellite, offline fallback
echo      httpx                  secure AI provider requests
echo.
echo   Keep this window open until every check passes.
echo   The first setup can take a few minutes.
echo.
echo   Continue only if you accept the Terms and bundled Tool License.
echo   Terms: https://fleece.wtf/terms
echo   Tool License: LICENSE in this folder
echo.
echo  ==================================================
echo.
if "%ASSUME_YES%"=="1" (
    echo   Continue with install or repair? [Y/N]: Y
) else (
    choice /C YN /N /M "  Continue with install or repair? [Y/N]: "
    if errorlevel 2 goto Cancelled
)

:SetupApprovalReady
call :ValidatePrivatePaths
if errorlevel 1 (
    set "FAIL_MESSAGE=The app folder or one of its private setup paths is not safe to modify. Extract a fresh copy to a normal folder and try again."
    goto Failed
)
set "PATHS_VALIDATED=1"
call :CheckRootWritePermission
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup cannot write to this app folder. Move it to a folder owned by this Windows user and try again."
    goto Failed
)
if not exist "%RUNTIME%" mkdir "%RUNTIME%" >nul 2>nul
if not exist "%RUNTIME%" (
    set "FAIL_MESSAGE=Could not create the private runtime folder."
    goto Failed
)
call :AcquireSetupLock
if errorlevel 1 goto SetupAlreadyRunning
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)

:PrepareSetupLog
if exist "%LOG%" del /f /q "%LOG%" >nul 2>nul
if exist "%LOG%" (
    set "FAIL_MESSAGE=The previous setup log could not be replaced safely."
    goto Failed
)
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$stream=[IO.File]::Open($env:LOG,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);$stream.Dispose()" >nul 2>nul
if errorlevel 1 (
    set "FAIL_MESSAGE=A fresh private setup log could not be created safely."
    goto Failed
)
set "LOG_READY=1"
set "DIAGNOSTIC_LOG=%LOG%"
call :EnsureAppClosed
if errorlevel 1 (
    set "FAIL_MESSAGE=AI Location Finder is open. Close the app before installing or repairing its files."
    goto Failed
)
if not exist "%DOWNLOADS%" mkdir "%DOWNLOADS%" >>"%LOG%" 2>&1
if not exist "%DOWNLOADS%" (
    set "FAIL_MESSAGE=Could not create the private download folder."
    goto Failed
)

set "LOG_MESSAGE============================================================"
call :LogCurrent
set "LOG_MESSAGE=Setup started."
call :LogCurrent
set "LOG_MESSAGE=Project root: %ROOT%"
call :LogCurrent
set "LOG_MESSAGE=Native architecture: %NATIVE_ARCH%"
call :LogCurrent
set "LOG_MESSAGE============================================================"
call :LogCurrent

if not exist "%APP_FILE%" (
    set "FAIL_MESSAGE=AI Location Finder.pyw is missing from this folder."
    goto Failed
)
if not exist "%PROVIDERS_FILE%" (
    set "FAIL_MESSAGE=location_providers.py is missing from this folder."
    goto Failed
)
if not exist "%MAP_MODULE%" (
    set "FAIL_MESSAGE=location_map.py is missing from this folder."
    goto Failed
)
if not exist "%PROMPTS_FILE%" (
    set "FAIL_MESSAGE=location_prompts.py is missing from this folder."
    goto Failed
)
if not exist "%CAPTURE_FILE%" (
    set "FAIL_MESSAGE=screen_capture.py is missing from this folder."
    goto Failed
)
if not exist "%MAP_ASSET%" (
    set "FAIL_MESSAGE=assets\world_map.png is missing from this folder."
    goto Failed
)

echo.
echo   [ STEP 1 / 3 ]   Private Python environment
echo.
call :ValidateEmbeddedPython
if not errorlevel 1 (
    if exist "%VENV%" call :RemoveDirectoryRobust "%VENV%"
    if exist "%VENV%" (
        set "FAIL_MESSAGE=An old .venv folder could not be removed after private Python was verified."
        goto Failed
    )
    echo      Existing private Python is valid. Keeping it.
    set "LOG_MESSAGE=Existing embedded CPython passed validation."
    call :LogCurrent
    set "ENV_MODE=embedded"
    set "APP_PY=%RUNTIME_PY%"
    set "APP_PYW=%RUNTIME_PYW%"
    goto PythonEnvironmentReady
)

echo      No verified private Python runtime is available yet.
echo.
:ExplainEmbeddedPython
echo      Setup can place Python %PYTHON_VERSION% privately inside
echo      this folder. It will not replace your current Python,
echo      change PATH, install global packages, or need admin.
echo.
echo.
echo      Downloading and preparing private Python...
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)
call :InstallEmbedPy
set "INSTALL_EMBEDDED_CODE=%ERRORLEVEL%"
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)
if not "%INSTALL_EMBEDDED_CODE%"=="0" (
    set "FAIL_MESSAGE=Private Python could not be installed or verified."
    goto Failed
)

if exist "%VENV%" call :RemoveDirectoryRobust "%VENV%"
if exist "%VENV%" (
    set "FAIL_MESSAGE=An invalid old .venv folder could not be removed."
    goto Failed
)
set "ENV_MODE=embedded"
set "APP_PY=%RUNTIME_PY%"
set "APP_PYW=%RUNTIME_PYW%"

:PythonEnvironmentReady
call :ValidateSelectedEnvironment
if errorlevel 1 (
    set "FAIL_MESSAGE=The private Python environment did not pass validation."
    goto Failed
)
echo      Done.

echo.
echo   [ STEP 2 / 3 ]   App components
echo.
echo      Installing or repairing trusted packages from PyPI...
echo      Existing components are reused whenever possible.
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)
call :InstallPythonPackages
set "INSTALL_PACKAGES_CODE=%ERRORLEVEL%"
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)
if not "%INSTALL_PACKAGES_CODE%"=="0" (
    set "FAIL_MESSAGE=PySide6 and httpx could not be installed and verified."
    goto Failed
)
echo      Done.

echo.
echo   [ STEP 3 / 3 ]   Final checks
echo.
echo      Testing source, monitor capture, prompts, and detailed
echo      street, satellite, and offline map logic without capturing
echo      your desktop, downloading map tiles, or making AI requests...
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)
call :VerifyEverything
set "VERIFY_EVERYTHING_CODE=%ERRORLEVEL%"
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)
if not "%VERIFY_EVERYTHING_CODE%"=="0" (
    set "FAIL_MESSAGE=One or more final component checks failed."
    goto Failed
)
echo      Creating the AI Location Finder start shortcut...
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)
call :CreateShortcut
if errorlevel 1 (
    set "FAIL_MESSAGE=The start shortcut could not be created."
    goto Failed
)
call :WriteSetupMarker
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup finished its checks but could not save the completion marker."
    goto Failed
)
echo      Every check passed.

if exist "%DOWNLOADS%" call :RemoveDirectoryRobust "%DOWNLOADS%"
if exist "%DOWNLOADS%" (
    set "FAIL_MESSAGE=Setup passed its checks but could not safely remove temporary downloads."
    goto Failed
)
set "LOG_MESSAGE=Setup completed successfully."
call :LogCurrent
call :ReleaseSetupLock

echo.
echo  ==================================================
echo                ALL SET, YOU ARE READY
echo  ==================================================
echo.
echo   Double click the "AI Location Finder" shortcut in this
echo   folder to start. You can copy the shortcut to your
echo   Desktop or pin it to the taskbar.
echo.
echo   Run this installer again whenever you want to
echo   repair the app's private local files or refresh the shortcut.
echo.
echo   Setup details were saved to:
echo   "%LOG%"
echo.
call :PauseIfNeeded
exit /b 0

:SetupAlreadyRunning
echo.
echo  ==================================================
echo                 SETUP ALREADY RUNNING
echo  ==================================================
echo.
echo   Another AI Location Finder setup is already running.
echo   Let that window finish, then try again.
echo.
call :PauseIfNeeded
exit /b 1

:Cancelled
call :ReleaseSetupLock
echo.
echo  ==================================================
echo                     SETUP CANCELLED
echo  ==================================================
echo.
echo   Nothing was installed or changed after cancellation.
echo   Run Installer.bat again whenever you are ready.
echo.
call :PauseIfNeeded
exit /b 1

:Failed
if not defined FAIL_MESSAGE set "FAIL_MESSAGE=Setup stopped because an unexpected error occurred."
set "LOG_MESSAGE=ERROR: %FAIL_MESSAGE%"
if defined LOG_READY call :LogCurrent
if defined PATHS_VALIDATED call :ReleaseSetupLock
echo.
echo  ==================================================
echo                     SETUP STOPPED
echo  ==================================================
echo.
echo   %FAIL_MESSAGE%
echo.
echo   No success was reported because all checks did not pass.
if defined LOG_READY (
    echo   The detailed log is here:
    echo.
    echo   "%LOG%"
) else (
    echo   No new log was written because setup stopped before it could safely own one.
)
echo.
echo   Fix the listed problem, then run Installer.bat again.
echo.
call :PauseIfNeeded
exit /b 1


:AcquireSetupLock
2>nul mkdir "%SETUP_LOCK%"
if not errorlevel 1 goto SetupLockCreated
call :ValidatePrivateTree "%SETUP_LOCK%"
if errorlevel 1 exit /b 1
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $lock=$env:SETUP_LOCK; $owner=$env:SETUP_LOCK_OWNER; $max=[double]$env:SETUP_LOCK_MAX_AGE_MINUTES; $fresh=(((Get-Date)-(Get-Item -LiteralPath $lock).CreationTime).TotalSeconds -lt 30); if($fresh){exit 2}; $owned=$false; $token=$null; if(Test-Path -LiteralPath $owner){try{$data=Get-Content -LiteralPath $owner -Raw -Encoding UTF8|ConvertFrom-Json; $token=[string]$data.token; $heartbeat=[DateTime]::Parse([string]$data.heartbeatUtc).ToUniversalTime(); $process=Get-CimInstance Win32_Process -Filter ('ProcessId=' + [int]$data.pid) -ErrorAction SilentlyContinue; if($process -and $process.Name -ieq 'cmd.exe'){$started=([DateTime]$process.CreationDate).ToUniversalTime(); $recorded=[DateTime]::Parse([string]$data.processStartedUtc).ToUniversalTime(); $sameProcess=[Math]::Abs(($started-$recorded).TotalSeconds) -lt 3; $dedicatedChild=($data.child -eq $true -and [string]$process.CommandLine -match '(?i)--fleece-setup-child(?:\s|$)'); if($sameProcess -and ($dedicatedChild -or ([DateTime]::UtcNow-$heartbeat).TotalMinutes -lt $max)){$owned=$true}}}catch{}}; if($owned){exit 2}; if(Test-Path -LiteralPath $owner){try{$latest=Get-Content -LiteralPath $owner -Raw -Encoding UTF8|ConvertFrom-Json; if($token -and [string]$latest.token -ne $token){exit 2}}catch{if($token){exit 2}}}; $stale=$lock+'.stale-'+[Guid]::NewGuid().ToString('N'); Move-Item -LiteralPath $lock -Destination $stale; Remove-Item -LiteralPath $stale -Recurse -Force" >nul 2>nul
if errorlevel 1 exit /b 1
2>nul mkdir "%SETUP_LOCK%"
if errorlevel 1 exit /b 1

:SetupLockCreated
set "SETUP_LOCK_HELD=1"
set "SETUP_LOCK_TOKEN_FILE=%SETUP_LOCK%\token.txt"
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -Command "[Guid]::NewGuid().ToString('N')" >"%SETUP_LOCK_TOKEN_FILE%" 2>nul
if exist "%SETUP_LOCK_TOKEN_FILE%" set /p "SETUP_LOCK_TOKEN="<"%SETUP_LOCK_TOKEN_FILE%"
del /f /q "%SETUP_LOCK_TOKEN_FILE%" >nul 2>nul
if not defined SETUP_LOCK_TOKEN goto SetupLockCreateFailed
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $self=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID); if(-not $self -or -not $self.ParentProcessId){throw 'Could not identify the setup process.'}; $parent=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $self.ParentProcessId); if(-not $parent){throw 'Could not identify the setup process.'}; if($env:SETUP_CHILD -ne '1' -or [string]$parent.CommandLine -notmatch '(?i)--fleece-setup-child(?:\s|$)'){throw 'Could not verify the dedicated setup child.'}; $started=([DateTime]$parent.CreationDate).ToUniversalTime().ToString('o'); $data=[ordered]@{schema=2;pid=[int]$parent.ProcessId;processStartedUtc=$started;token=$env:SETUP_LOCK_TOKEN;heartbeatUtc=[DateTime]::UtcNow.ToString('o');child=$true}; $new=$env:SETUP_LOCK_OWNER+'.new'; $data|ConvertTo-Json -Compress|Set-Content -LiteralPath $new -Encoding UTF8; Move-Item -LiteralPath $new -Destination $env:SETUP_LOCK_OWNER -Force" >nul 2>nul
if not errorlevel 1 exit /b 0

:SetupLockCreateFailed
del /f /q "%SETUP_LOCK_OWNER%" >nul 2>nul
rmdir "%SETUP_LOCK%" >nul 2>nul
set "SETUP_LOCK_HELD=0"
set "SETUP_LOCK_TOKEN="
exit /b 1

:EnsureAppClosed
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "foreach($name in @('Global\FleeceAILocationFinderApp','Local\FleeceAILocationFinderApp')){try{$mutex=[Threading.Mutex]::OpenExisting($name);$mutex.Dispose();exit 1}catch [Threading.WaitHandleCannotBeOpenedException]{}catch{exit 1}};exit 0" >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:CheckRootWritePermission
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$root=[IO.Path]::GetFullPath($env:ROOT).TrimEnd('\');$probe=Join-Path $root ('.fleece-write-test-'+[Guid]::NewGuid().ToString('N')+'.tmp');try{$stream=[IO.File]::Open($probe,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);$stream.Dispose()}finally{if(Test-Path -LiteralPath $probe){Remove-Item -LiteralPath $probe -Force}};exit 0" >nul 2>nul
exit /b %ERRORLEVEL%

:ValidatePrivatePaths
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$root=[IO.Path]::GetFullPath($env:ROOT).TrimEnd('\');$volume=[IO.Path]::GetPathRoot($root).TrimEnd('\');if([string]::IsNullOrWhiteSpace($root)-or $root -ieq $volume){throw 'Unsafe project root.'};$rootItem=Get-Item -LiteralPath $root -Force;if(-not $rootItem.PSIsContainer-or($rootItem.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'The project root must be a normal directory.'};$targets=@($env:RUNTIME,$env:VENV,$env:DOWNLOADS,$env:PYTHON_DIR,(Join-Path $env:PYTHON_DIR 'Lib'),$env:LOCAL_SITE,$env:SETUP_LOCK,($env:PYTHON_DIR+'.new'),($env:PYTHON_DIR+'.old'),($env:VENV+'.old'),(Join-Path $env:RUNTIME 'b'),(Join-Path $env:RUNTIME 'b.new'),(Join-Path $env:RUNTIME 'b.old'),(Join-Path $env:RUNTIME 'setup-check'));$prefix=$root+'\';foreach($target in $targets){if([string]::IsNullOrWhiteSpace($target)){throw 'A private setup path is empty.'};$full=[IO.Path]::GetFullPath($target).TrimEnd('\');if(-not $full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'A private setup path escaped the project root.'};if(Test-Path -LiteralPath $full){$item=Get-Item -LiteralPath $full -Force;if(-not $item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'A private setup directory is unsafe.'}}};foreach($file in @($env:LOG,$env:SETUP_MARKER,($env:SETUP_MARKER+'.new'),$env:SETUP_LOCK_OWNER,($env:SETUP_LOCK_OWNER+'.new'),$env:PIP_WHEEL)){if([string]::IsNullOrWhiteSpace($file)){continue};$full=[IO.Path]::GetFullPath($file);if(-not $full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'A private setup file escaped the project root.'};if(Test-Path -LiteralPath $full){$item=Get-Item -LiteralPath $full -Force;if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'A private setup file is unsafe.'}}};exit 0" >nul 2>nul
exit /b %ERRORLEVEL%

:WriteSetupMarker
if /I not "%ENV_MODE%"=="embedded" exit /b 1
>"%SETUP_MARKER%.new" echo embedded
if errorlevel 1 exit /b 1
move /y "%SETUP_MARKER%.new" "%SETUP_MARKER%" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
if not exist "%SETUP_MARKER%" exit /b 1
exit /b 0

:ReleaseSetupLock
if not "%SETUP_LOCK_HELD%"=="1" exit /b 0
call :ValidatePrivateTree "%SETUP_LOCK%"
if errorlevel 1 exit /b 2
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; if(-not(Test-Path -LiteralPath $env:SETUP_LOCK_OWNER)){exit 2}; $data=Get-Content -LiteralPath $env:SETUP_LOCK_OWNER -Raw -Encoding UTF8|ConvertFrom-Json; if([string]$data.token -ne $env:SETUP_LOCK_TOKEN){exit 2}; $released=$env:SETUP_LOCK+'.released-'+[Guid]::NewGuid().ToString('N'); Move-Item -LiteralPath $env:SETUP_LOCK -Destination $released; Remove-Item -LiteralPath $released -Recurse -Force" >nul 2>nul
set "RELEASE_LOCK_CODE=%ERRORLEVEL%"
set "SETUP_LOCK_HELD=0"
set "SETUP_LOCK_TOKEN="
exit /b %RELEASE_LOCK_CODE%

:TouchSetupLock
if not "%SETUP_LOCK_HELD%"=="1" exit /b 0
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $data=Get-Content -LiteralPath $env:SETUP_LOCK_OWNER -Raw -Encoding UTF8|ConvertFrom-Json; if([string]$data.token -ne $env:SETUP_LOCK_TOKEN){exit 2}; $data.heartbeatUtc=[DateTime]::UtcNow.ToString('o'); $new=$env:SETUP_LOCK_OWNER+'.new'; $data|ConvertTo-Json -Compress|Set-Content -LiteralPath $new -Encoding UTF8; Move-Item -LiteralPath $new -Destination $env:SETUP_LOCK_OWNER -Force" >nul 2>nul
exit /b %ERRORLEVEL%


:ValidateEmbeddedPython
call :ValidateEmbeddedPythonAt "%PYTHON_DIR%"
exit /b %ERRORLEVEL%

:ValidateEmbeddedPythonAt
if "%~1"=="" exit /b 1
if not exist "%~1\python.exe" exit /b 1
if not exist "%~1\pythonw.exe" exit /b 1
if not exist "%~1\Lib\site-packages" exit /b 1
if not exist "%~1\pip.whl" exit /b 1
call :VerifyFileHash "%~1\pip.whl" "%PIP_WHEEL_SHA256%"
if errorlevel 1 exit /b 1
"%~1\python.exe" -I -c "import sys, struct, site; ok = sys.implementation.name == 'cpython' and sys.version_info[:3] == (3, 14, 7) and struct.calcsize('P') == 8 and any(p.lower().endswith(r'lib\site-packages') for p in sys.path); raise SystemExit(0 if ok else 1)" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
"%~1\python.exe" -I -c "import sys; sys.path.insert(0, sys.argv[1]); from pip._internal.cli.main import main; raise SystemExit(main(sys.argv[2:]))" "%~1\pip.whl" --version >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:InstallEmbedPy
call :ValidateEmbeddedPython
if not errorlevel 1 exit /b 0

set "PYTHON_ARCHIVE=%DOWNLOADS%\python-%PYTHON_VERSION%-embed-%ARCH%.zip"
set "PYTHON_NEW=%RUNTIME%\python.new"
set "PIP_DOWNLOAD=%DOWNLOADS%\pip.whl"
call :DownloadAndVerify "%PYTHON_URL%" "%PYTHON_ARCHIVE%" "%PYTHON_SHA256%"
if errorlevel 1 exit /b 1
call :DownloadAndVerify "%PIP_WHEEL_URL%" "%PIP_DOWNLOAD%" "%PIP_WHEEL_SHA256%"
if errorlevel 1 exit /b 1

if exist "%PYTHON_NEW%" call :RemoveDirectoryRobust "%PYTHON_NEW%"
if exist "%PYTHON_NEW%" exit /b 1
set "ARCHIVE_FILE=%PYTHON_ARCHIVE%"
set "NEW_DIR=%PYTHON_NEW%"
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath $env:ARCHIVE_FILE -DestinationPath $env:NEW_DIR -Force; $pth=Get-ChildItem -LiteralPath $env:NEW_DIR -Filter 'python*._pth' -File | Select-Object -First 1; if(-not $pth){throw 'Python archive did not contain its path configuration.'}; $lines=@(Get-Content -LiteralPath $pth.FullName | Where-Object { $_ -notmatch '^\s*#?\s*import site\s*$' -and $_ -notmatch '^\s*Lib\\site-packages\s*$' }); $lines += 'Lib\site-packages'; $lines += 'import site'; Set-Content -LiteralPath $pth.FullName -Value $lines -Encoding ASCII; New-Item -ItemType Directory -Path (Join-Path $env:NEW_DIR 'Lib\site-packages') -Force | Out-Null; Copy-Item -LiteralPath $env:PIP_DOWNLOAD -Destination (Join-Path $env:NEW_DIR 'pip.whl') -Force" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1

call :ValidateEmbeddedPythonAt "%PYTHON_NEW%"
set "TEMP_VALIDATE_CODE=%ERRORLEVEL%"
if not "%TEMP_VALIDATE_CODE%"=="0" exit /b 1

call :ReplaceDirectory "%PYTHON_NEW%" "%PYTHON_DIR%"
if errorlevel 1 exit /b 1
del /f /q "%PYTHON_ARCHIVE%" "%PIP_DOWNLOAD%" >nul 2>nul
call :ValidateEmbeddedPython
if errorlevel 1 exit /b 1
set "LOG_MESSAGE=Official embedded CPython passed local validation."
call :LogCurrent
exit /b 0

:ValidateSelectedEnvironment
if /I not "%ENV_MODE%"=="embedded" exit /b 1
call :ValidateEmbeddedPython
exit /b %ERRORLEVEL%

:InstallPythonPackages
if not defined APP_PY exit /b 1
if not exist "%APP_PY%" exit /b 1
call :CurrentPackagesFullyHealthy
if not errorlevel 1 exit /b 0
call :BeginPackageTransaction
if errorlevel 1 exit /b 1
call :InstallEmbeddedPackages
set "PACKAGE_TRANSACTION_CODE=%ERRORLEVEL%"
call :FinishPackageTransaction %PACKAGE_TRANSACTION_CODE%
exit /b %ERRORLEVEL%

:CurrentPackagesFullyHealthy
call :HasPinnedPackages
if errorlevel 1 exit /b 1
call :VerifyPythonPackages
exit /b %ERRORLEVEL%

:BeginPackageTransaction
if /I not "%ENV_MODE%"=="embedded" exit /b 1
set "PACKAGE_BACKUP=%RUNTIME%\b"
set "PACKAGE_BACKUP_NEW=%PACKAGE_BACKUP%.new"
set "PACKAGE_TARGET=%PYTHON_DIR%"
set "PACKAGE_BACKUP_PROBE=python.exe"
if exist "%PACKAGE_BACKUP%" (
    call :ValidatePrivateTree "%PACKAGE_BACKUP%"
    if errorlevel 1 exit /b 1
    if not exist "%PACKAGE_BACKUP%\%PACKAGE_BACKUP_PROBE%" exit /b 1
    set "LOG_MESSAGE=Recovering the local package environment left by an interrupted repair."
    call :LogCurrent
    call :ReplaceDirectory "%PACKAGE_BACKUP%" "%PACKAGE_TARGET%"
    if errorlevel 1 exit /b 1
)
if not exist "%PACKAGE_TARGET%" exit /b 1
call :ValidatePrivateTree "%PACKAGE_TARGET%"
if errorlevel 1 exit /b 1
if exist "%PACKAGE_BACKUP_NEW%" call :RemoveDirectoryRobust "%PACKAGE_BACKUP_NEW%"
if exist "%PACKAGE_BACKUP_NEW%" exit /b 1
set "LOG_MESSAGE=Creating a local rollback copy before package repair."
call :LogCurrent
"%ROBOCOPY_EXE%" "%PACKAGE_TARGET%" "%PACKAGE_BACKUP_NEW%" /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XJ /NFL /NDL /NJH /NJS /NP >>"%LOG%" 2>&1
if errorlevel 8 exit /b 1
call :ValidatePrivateTree "%PACKAGE_BACKUP_NEW%"
if errorlevel 1 exit /b 1
if not exist "%PACKAGE_BACKUP_NEW%\%PACKAGE_BACKUP_PROBE%" exit /b 1
move "%PACKAGE_BACKUP_NEW%" "%PACKAGE_BACKUP%" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
if not exist "%PACKAGE_BACKUP%" exit /b 1
call :ValidatePrivateTree "%PACKAGE_BACKUP%"
if errorlevel 1 exit /b 1
if exist "%PACKAGE_BACKUP_NEW%" exit /b 1
exit /b 0

:FinishPackageTransaction
set "PACKAGE_TRANSACTION_CODE=%~1"
if "%PACKAGE_TRANSACTION_CODE%"=="0" (
    if exist "%PACKAGE_BACKUP%" call :RemoveDirectoryRobust "%PACKAGE_BACKUP%"
    if exist "%PACKAGE_BACKUP%" exit /b 1
    exit /b 0
)
set "LOG_MESSAGE=Package repair failed; restoring the previous private Python environment."
call :LogCurrent
call :ReplaceDirectory "%PACKAGE_BACKUP%" "%PACKAGE_TARGET%"
if errorlevel 1 exit /b 1
exit /b %PACKAGE_TRANSACTION_CODE%

:InstallEmbeddedPackages
call :ValidateEmbeddedPython
if errorlevel 1 exit /b 1
call :HasPinnedPackages
if errorlevel 1 goto InstallFullEmbeddedPackages
call :VerifyPythonPackages
if not errorlevel 1 exit /b 0

:InstallFullEmbeddedPackages
set "LOG_MESSAGE=Installing pinned %PYSIDE_DISTRIBUTION% %PYSIDE_VERSION%, httpx %HTTPX_VERSION%, and anyio %ANYIO_VERSION% into embedded CPython from official PyPI."
call :LogCurrent
call :ResetEmbeddedPackages
if errorlevel 1 exit /b 1
"%APP_PY%" -I -c "import sys; sys.path.insert(0, sys.argv[1]); from pip._internal.cli.main import main; raise SystemExit(main(sys.argv[2:]))" "%PIP_WHEEL%" --isolated --disable-pip-version-check install --upgrade --no-cache-dir --only-binary=:all: --index-url "%PYPI_INDEX%" --target "%LOCAL_SITE%" %PYTHON_PACKAGES% >>"%LOG%" 2>&1
set "PACKAGE_INSTALL_CODE=%ERRORLEVEL%"

:CheckInstalledPackages
if not "%PACKAGE_INSTALL_CODE%"=="0" goto RepairPythonPackages
call :VerifyPythonPackages
if not errorlevel 1 exit /b 0

:RepairPythonPackages
echo      A component check failed. Repairing local packages...
set "LOG_MESSAGE=Initial package validation failed; forcing a clean package reinstall."
call :LogCurrent
if /I not "%ENV_MODE%"=="embedded" exit /b 1
call :ResetEmbeddedPackages
if errorlevel 1 exit /b 1
"%APP_PY%" -I -c "import sys; sys.path.insert(0, sys.argv[1]); from pip._internal.cli.main import main; raise SystemExit(main(sys.argv[2:]))" "%PIP_WHEEL%" --isolated --disable-pip-version-check install --upgrade --force-reinstall --no-cache-dir --only-binary=:all: --index-url "%PYPI_INDEX%" --target "%LOCAL_SITE%" %PYTHON_PACKAGES% >>"%LOG%" 2>&1

:RepairPackagesFinished
if errorlevel 1 exit /b 1
call :VerifyPythonPackages
exit /b %ERRORLEVEL%

:VerifyPythonPackages
if not defined APP_PY exit /b 1
if not exist "%APP_PY%" exit /b 1
"%APP_PY%" -I -c "import anyio, httpx, os, re, PySide6; from importlib.metadata import distributions, version; from PySide6.QtCore import qVersion; from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache; canonical=lambda value: re.sub(r'[-_.]+','-',value).lower(); expected={canonical(name): package_version for item in os.environ['PYTHON_PACKAGES'].split() for name,package_version in [item.split('==',1)]}; entries=[(canonical(dist.metadata['Name']),dist.version) for dist in distributions() if dist.metadata.get('Name')]; assert len(entries)==len(expected) and dict(entries)==expected; assert hasattr(httpx, 'Client') and hasattr(httpx, 'AsyncClient'); assert QNetworkAccessManager and QNetworkDiskCache; print('Exact private package manifest: ' + ', '.join(name + '=' + expected[name] for name in sorted(expected))); print('Qt=' + qVersion())" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
if /I not "%ENV_MODE%"=="embedded" exit /b 1
"%APP_PY%" -I -c "import sys; sys.path.insert(0, sys.argv[1]); from pip._internal.cli.main import main; raise SystemExit(main(sys.argv[2:]))" "%PIP_WHEEL%" --isolated --disable-pip-version-check check >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:HasPinnedPackages
if not defined APP_PY exit /b 1
if not exist "%APP_PY%" exit /b 1
"%APP_PY%" -I -c "import anyio, httpx, os, re, PySide6; from importlib.metadata import distributions; from PySide6.QtNetwork import QNetworkAccessManager; canonical=lambda value: re.sub(r'[-_.]+','-',value).lower(); expected={canonical(name): package_version for item in os.environ['PYTHON_PACKAGES'].split() for name,package_version in [item.split('==',1)]}; entries=[(canonical(dist.metadata['Name']),dist.version) for dist in distributions() if dist.metadata.get('Name')]; ok=len(entries)==len(expected) and dict(entries)==expected and bool(QNetworkAccessManager); raise SystemExit(0 if ok else 1)" >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:ResetEmbeddedPackages
if /I not "%ENV_MODE%"=="embedded" exit /b 1
call :RemoveDirectoryRobust "%LOCAL_SITE%"
if errorlevel 1 exit /b 1
mkdir "%LOCAL_SITE%" >>"%LOG%" 2>&1
if not exist "%LOCAL_SITE%" exit /b 1
exit /b 0

:RemoveDirectoryRobust
set "REMOVE_TREE=%~1"
if not defined REMOVE_TREE exit /b 1
if not exist "%REMOVE_TREE%" exit /b 0
call :ValidatePrivateTree "%REMOVE_TREE%"
if errorlevel 1 exit /b 1
set "EMPTY_TREE=%RUNTIME%\empty-%RANDOM%-%RANDOM%"
if exist "%EMPTY_TREE%" exit /b 1
mkdir "%EMPTY_TREE%" >>"%LOG%" 2>&1
if not exist "%EMPTY_TREE%" exit /b 1
call :ValidatePrivateTree "%EMPTY_TREE%"
if errorlevel 1 exit /b 1
"%ROBOCOPY_EXE%" "%EMPTY_TREE%" "%REMOVE_TREE%" /MIR /R:2 /W:1 /XJ /NFL /NDL /NJH /NJS /NP /NC /NS >nul 2>>"%LOG%"
if errorlevel 8 exit /b 1
rmdir /s /q "%REMOVE_TREE%" >>"%LOG%" 2>&1
rmdir /s /q "%EMPTY_TREE%" >>"%LOG%" 2>&1
if exist "%REMOVE_TREE%" exit /b 1
if exist "%EMPTY_TREE%" exit /b 1
exit /b 0

:ValidatePrivateTree
if "%~1"=="" exit /b 1
set "VALIDATE_TREE=%~1"
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$project=[IO.Path]::GetFullPath($env:ROOT).TrimEnd('\');$root=[IO.Path]::GetFullPath($env:VALIDATE_TREE).TrimEnd('\');if(-not $root.StartsWith($project+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Private tree escaped the project root.'};$stack=New-Object 'System.Collections.Generic.Stack[string]';$stack.Push($root);while($stack.Count -gt 0){$directory=Get-Item -LiteralPath $stack.Pop() -Force;if(-not $directory.PSIsContainer-or($directory.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Unsafe private directory.'};foreach($entryPath in [IO.Directory]::EnumerateFileSystemEntries($directory.FullName)){$entry=Get-Item -LiteralPath $entryPath -Force;if($entry.Attributes-band[IO.FileAttributes]::ReparsePoint){throw 'Unsafe private reparse point.'};if($entry.PSIsContainer){$stack.Push($entry.FullName)}}};exit 0" >>"%DIAGNOSTIC_LOG%" 2>&1
exit /b %ERRORLEVEL%

:ReplaceDirectory
set "REPLACE_NEW=%~1"
set "REPLACE_TARGET=%~2"
set "REPLACE_BACKUP=%~2.old"
if not exist "%REPLACE_NEW%" exit /b 1
call :ValidatePrivateTree "%REPLACE_NEW%"
if errorlevel 1 exit /b 1
if exist "%REPLACE_TARGET%" (
    call :ValidatePrivateTree "%REPLACE_TARGET%"
    if errorlevel 1 exit /b 1
)
if exist "%REPLACE_BACKUP%" (
    call :ValidatePrivateTree "%REPLACE_BACKUP%"
    if errorlevel 1 exit /b 1
    if exist "%REPLACE_TARGET%" (
        call :RemoveDirectoryRobust "%REPLACE_BACKUP%"
        if errorlevel 1 exit /b 1
        if exist "%REPLACE_BACKUP%" exit /b 1
    ) else (
        move "%REPLACE_BACKUP%" "%REPLACE_TARGET%" >>"%LOG%" 2>&1
        if errorlevel 1 exit /b 1
        if exist "%REPLACE_BACKUP%" exit /b 1
        call :ValidatePrivateTree "%REPLACE_TARGET%"
        if errorlevel 1 exit /b 1
    )
)
if not exist "%REPLACE_TARGET%" goto ReplaceMoveNew
move "%REPLACE_TARGET%" "%REPLACE_BACKUP%" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1

:ReplaceMoveNew
move "%REPLACE_NEW%" "%REPLACE_TARGET%" >>"%LOG%" 2>&1
if errorlevel 1 goto ReplaceRollback
if exist "%REPLACE_BACKUP%" (
    call :RemoveDirectoryRobust "%REPLACE_BACKUP%"
    if errorlevel 1 exit /b 1
)
if exist "%REPLACE_BACKUP%" exit /b 1
exit /b 0

:ReplaceRollback
if exist "%REPLACE_TARGET%" (
    call :RemoveDirectoryRobust "%REPLACE_TARGET%"
    if errorlevel 1 exit /b 1
)
if exist "%REPLACE_TARGET%" exit /b 1
if not exist "%REPLACE_BACKUP%" exit /b 1
call :ValidatePrivateTree "%REPLACE_BACKUP%"
if errorlevel 1 exit /b 1
move "%REPLACE_BACKUP%" "%REPLACE_TARGET%" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
if exist "%REPLACE_BACKUP%" exit /b 1
if not exist "%REPLACE_TARGET%" exit /b 1
call :ValidatePrivateTree "%REPLACE_TARGET%"
if errorlevel 1 exit /b 1
exit /b 1

:DownloadAndVerify
set "DL_URL=%~1"
set "DL_FILE=%~2"
set "DL_HASH=%~3"
if not defined DL_HASH exit /b 1
if not exist "%DL_FILE%" goto DownloadFresh
call :VerifyFileHash "%DL_FILE%" "%DL_HASH%"
if not errorlevel 1 (
    set "LOG_MESSAGE=Reusing an already downloaded file that passed SHA-256 verification: %DL_FILE%"
    call :LogCurrent
    exit /b 0
)
del /f /q "%DL_FILE%" >nul 2>nul

:DownloadFresh
if exist "%DL_FILE%" del /f /q "%DL_FILE%" >nul 2>nul
set "LOG_MESSAGE=Downloading: %DL_URL%"
call :LogCurrent

if not exist "%CURL_EXE%" goto DownloadWithPowerShell
"%CURL_EXE%" --fail --location --silent --show-error --retry 3 --retry-delay 2 --connect-timeout 30 --proto "=https" --proto-redir "=https" -o "%DL_FILE%" "%DL_URL%" >>"%LOG%" 2>&1
if not errorlevel 1 goto VerifyDownload
set "LOG_MESSAGE=curl failed; retrying with PowerShell."
call :LogCurrent

:DownloadWithPowerShell
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -TimeoutSec 300 -Uri $env:DL_URL -OutFile $env:DL_FILE" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1

:VerifyDownload
if not exist "%DL_FILE%" exit /b 1
call :VerifyFileHash "%DL_FILE%" "%DL_HASH%"
exit /b %ERRORLEVEL%

:VerifyFileHash
set "VERIFY_FILE=%~1"
set "VERIFY_HASH=%~2"
if not exist "%VERIFY_FILE%" exit /b 1
if not defined VERIFY_HASH exit /b 1
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $stream=[IO.File]::OpenRead($env:VERIFY_FILE); try{$sha=[Security.Cryptography.SHA256]::Create(); try{$actual=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','')} finally{$sha.Dispose()}} finally{$stream.Dispose()}; if([string]::IsNullOrWhiteSpace($env:VERIFY_HASH)){Write-Output ('Recorded SHA-256: ' + $actual); exit 0}; if($actual -ne $env:VERIFY_HASH){throw ('SHA-256 mismatch. Expected {0}, got {1}' -f $env:VERIFY_HASH,$actual)}; Write-Output ('Verified SHA-256: ' + $actual)" >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:VerifyEverything
if not defined APP_PY exit /b 1
if not defined APP_PYW exit /b 1
if not exist "%APP_PY%" exit /b 1
if not exist "%APP_PYW%" exit /b 1
call :ValidateSelectedEnvironment
if errorlevel 1 exit /b 1
call :VerifyPythonPackages
if errorlevel 1 exit /b 1

"%APP_PY%" -I -c "import os; from pathlib import Path; files=[Path(os.environ[name]) for name in ('APP_FILE', 'PROVIDERS_FILE', 'MAP_MODULE', 'PROMPTS_FILE', 'CAPTURE_FILE')]; assert all(path.is_file() for path in files); [compile(path.read_text(encoding='utf-8'), str(path), 'exec') for path in files]; asset=Path(os.environ['MAP_ASSET']); assert asset.is_file() and asset.stat().st_size > 0; from PySide6.QtGui import QImage; assert not QImage(str(asset)).isNull(); from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache; assert QNetworkAccessManager and QNetworkDiskCache; print('Application sources, detailed map support, and offline map asset verified successfully.')" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
set "CHECK_DIR=%RUNTIME%\setup-check"
if exist "%CHECK_DIR%" call :RemoveDirectoryRobust "%CHECK_DIR%"
if exist "%CHECK_DIR%" exit /b 1
mkdir "%CHECK_DIR%" >>"%LOG%" 2>&1
if not exist "%CHECK_DIR%" exit /b 1
set "APP_CHECK_CODE=0"
"%APP_PY%" -I "%APP_FILE%" --install-check "%CHECK_DIR%" >>"%LOG%" 2>&1
if errorlevel 1 set "APP_CHECK_CODE=1"
if not "%APP_CHECK_CODE%"=="0" goto AppCheckCleanup
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $items=@(Get-ChildItem -LiteralPath $env:CHECK_DIR -Force); if($items.Count -ne 1){throw 'Install check must create exactly one result file.'}; $item=$items[0]; if($item.PSIsContainer -or $item.Name -cne 'checks.json'){throw 'Install check did not create only checks.json.'}; $data=Get-Content -LiteralPath $item.FullName -Raw | ConvertFrom-Json; if($null -eq $data){throw 'checks.json did not contain a JSON result.'}; foreach($name in @('passed','app','version','network_requests','real_desktop_captures','providers','model_entries','checks')){if($data.PSObject.Properties.Name -notcontains $name){throw ('checks.json is missing ' + $name)}}; if($data.passed -isnot [bool] -or -not $data.passed){throw 'App install check did not pass.'}; if($data.app -isnot [string] -or $data.app -cne 'AI Location Finder'){throw 'checks.json reported the wrong app.'}; if($data.version -isnot [string] -or $data.version -cne '1.0.10'){throw 'checks.json reported the wrong app version.'}; foreach($name in @('network_requests','real_desktop_captures','providers','model_entries')){if($data.$name -isnot [int] -and $data.$name -isnot [long]){throw ('checks.json has a non-integer ' + $name)}}; if($data.network_requests -ne 0 -or $data.real_desktop_captures -ne 0){throw 'App install check used network requests or desktop capture.'}; if($data.providers -ne 4){throw 'App install check reported the wrong provider count.'}; if($data.model_entries -lt 1){throw 'App install check did not report any models.'}; if($data.checks -isnot [System.Array]){throw 'App install checks must be an array.'}; $checks=@($data.checks); if($checks.Count -ne 7){throw 'App install check did not complete the expected checks.'}; foreach($check in $checks){if($check -isnot [string] -or [string]::IsNullOrWhiteSpace($check)){throw 'App install check contained an empty check.'}}; Write-Output 'Safe app install-check output verified.'" >>"%LOG%" 2>&1
if errorlevel 1 set "APP_CHECK_CODE=1"

:AppCheckCleanup
call :RemoveDirectoryRobust "%CHECK_DIR%"
if exist "%CHECK_DIR%" exit /b 1
if not "%APP_CHECK_CODE%"=="0" exit /b 1
exit /b 0

:CreateShortcut
set "LINK_PATH=%ROOT%AI Location Finder.lnk"
set "LINK_NEW=%RUNTIME%\shortcut.new.lnk"
set "LINK_BACKUP=%RUNTIME%\shortcut.previous.lnk"
set "LINK_TARGET=%APP_PYW%"
set "LINK_DIR=%ROOT%"
set "LINK_DESCRIPTION=AI Location Finder"
set "LINK_ICON=%APP_PYW%,0"
if not exist "%LINK_TARGET%" exit /b 1
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $path=$env:LINK_PATH; $new=$env:LINK_NEW; $backup=$env:LINK_BACKUP; $arguments='-I '+[char]34+$env:APP_FILE+[char]34; $samePath={param($a,$b) [IO.Path]::GetFullPath($a).TrimEnd('\') -ieq [IO.Path]::GetFullPath($b).TrimEnd('\')}; $verify={param($shortcut,$stage) if(-not(& $samePath $shortcut.TargetPath $env:LINK_TARGET) -or $shortcut.Arguments -cne $arguments -or -not(& $samePath $shortcut.WorkingDirectory $env:LINK_DIR) -or $shortcut.Description -cne $env:LINK_DESCRIPTION -or [int]$shortcut.WindowStyle -ne 1 -or ($shortcut.IconLocation-replace ',\s+',',') -ine ($env:LINK_ICON-replace ',\s+',',') -or $shortcut.Hotkey){throw ($stage+' shortcut did not preserve its isolated launcher contract.')}}; if(Test-Path -LiteralPath $backup){if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $backup -Force}else{Move-Item -LiteralPath $backup -Destination $path}}; if(Test-Path -LiteralPath $new){Remove-Item -LiteralPath $new -Force}; $shell=New-Object -ComObject WScript.Shell; $link=$shell.CreateShortcut($new); $link.TargetPath=$env:LINK_TARGET; $link.Arguments=$arguments; $link.WorkingDirectory=$env:LINK_DIR; $link.WindowStyle=1; $link.Description=$env:LINK_DESCRIPTION; $link.IconLocation=$env:LINK_ICON; $link.Hotkey=''; $link.Save(); $candidate=$shell.CreateShortcut($new); & $verify $candidate 'New'; $hadOld=Test-Path -LiteralPath $path; $movedOld=$false; try{if($hadOld){Move-Item -LiteralPath $path -Destination $backup; $movedOld=$true}; Move-Item -LiteralPath $new -Destination $path; $verified=$shell.CreateShortcut($path); & $verify $verified 'Installed'; if(Test-Path -LiteralPath $backup){Remove-Item -LiteralPath $backup -Force}; Write-Output ('Created and validated shortcut: ' + $path)}catch{if($movedOld){if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path -Force}; if(Test-Path -LiteralPath $backup){Move-Item -LiteralPath $backup -Destination $path}}elseif(-not $hadOld -and (Test-Path -LiteralPath $path)){Remove-Item -LiteralPath $path -Force}; throw}finally{if(Test-Path -LiteralPath $new){Remove-Item -LiteralPath $new -Force}}" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
if not exist "%LINK_PATH%" exit /b 1
exit /b 0

:LogCurrent
if not defined PATHS_VALIDATED exit /b 1
if not defined LOG_MESSAGE exit /b 0
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $line='[{0:yyyy-MM-dd HH:mm:ss.fff}] {1}{2}' -f [DateTime]::Now,$env:LOG_MESSAGE,[Environment]::NewLine; [IO.File]::AppendAllText($env:LOG,$line,[Text.UTF8Encoding]::new($false))" >nul 2>nul
set "LOG_MESSAGE="
exit /b %ERRORLEVEL%

:PauseIfNeeded
if "%NO_PAUSE%"=="1" exit /b 0
pause
exit /b 0
