@echo off
setlocal EnableExtensions DisableDelayedExpansion
title AI Location Finder Setup
set "INSTALLER_SELF=%~f0"
set "INSTALLER_ROOT=%~dp0"

set "NO_PAUSE=0"
set "ASSUME_YES=0"
set "SETUP_CHILD=0"
set "SKIP_ASSOCIATION=0"
set "TEST_ASSOCIATION=0"
set "ASSOCIATION_WARNING=0"
set "LOG_READY="
set "DIAGNOSTIC_LOG=nul"
set "PATHS_VALIDATED="
set "FFMPEG_DIR="
set "DENO_DIR="
set "HERCULES_DIR="
set "LUA_DIR="

:ParseArguments
if "%~1"=="" goto ArgumentsReady
if /I "%~1"=="--no-pause" goto ParseNoPause
if /I "%~1"=="--yes" goto ParseYes
if /I "%~1"=="--skip-association" goto ParseSkipAssociation
if /I "%~1"=="--test-association" goto ParseTestAssociation
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
echo   Supported options: --yes --no-pause --skip-association --test-association
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

:ParseSkipAssociation
set "SKIP_ASSOCIATION=1"
shift
goto ParseArguments

:ParseTestAssociation
set "TEST_ASSOCIATION=1"
set "NO_PAUSE=1"
shift
goto ParseArguments

:ArgumentsReady
if "%SETUP_CHILD%"=="1" goto DedicatedChildReady
set "SETUP_CHILD_ARGS=--fleece-setup-child"
if "%ASSUME_YES%"=="1" set "SETUP_CHILD_ARGS=%SETUP_CHILD_ARGS% --yes"
if "%NO_PAUSE%"=="1" set "SETUP_CHILD_ARGS=%SETUP_CHILD_ARGS% --no-pause"
if "%SKIP_ASSOCIATION%"=="1" set "SETUP_CHILD_ARGS=%SETUP_CHILD_ARGS% --skip-association"
if "%TEST_ASSOCIATION%"=="1" set "SETUP_CHILD_ARGS=%SETUP_CHILD_ARGS% --test-association"
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
set "VENV_PY=%VENV%\Scripts\python.exe"
set "VENV_PYW=%VENV%\Scripts\pythonw.exe"
set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "CURL_EXE=%SystemRoot%\System32\curl.exe"
set "ROBOCOPY_EXE=%SystemRoot%\System32\robocopy.exe"
set "ASSOCIATION_SHARED_DIR=%LOCALAPPDATA%\Fleece Tools\Python Launcher"
set "ASSOC_LAUNCHER_SHA256=4242BB5D1B0A26185AB2E817693BF12837B1CE5E68ECD83938758073EA7949BA"
set "ASSOC_RESTORE_SHA256=8AE3911863EED58BFD85D31155FDA460CF3C7F026A367057A9397D8C1C340880"
set "ASSOC_LAUNCHER_B64=T3B0aW9uIEV4cGxpY2l0DQoNCkRpbSBzaGVsbCwgZnNvLCBzY3JpcHRQYXRoLCB0b29sRGlyLCBweXRob253LCBjb21tYW5kTGluZSwgaW5kZXgNClNldCBzaGVsbCA9IENyZWF0ZU9iamVjdCgiV1NjcmlwdC5TaGVsbCIpDQpTZXQgZnNvID0gQ3JlYXRlT2JqZWN0KCJTY3JpcHRpbmcuRmlsZVN5c3RlbU9iamVjdCIpDQoNCklmIFdTY3JpcHQuQXJndW1lbnRzLkNvdW50IDwgMSBUaGVuIFdTY3JpcHQuUXVpdCAyDQoNCnNjcmlwdFBhdGggPSBmc28uR2V0QWJzb2x1dGVQYXRoTmFtZShXU2NyaXB0LkFyZ3VtZW50cygwKSkNCklmIE5vdCBmc28uRmlsZUV4aXN0cyhzY3JpcHRQYXRoKSBUaGVuDQogICAgTXNnQm94ICJUaGUgc2VsZWN0ZWQgUHl0aG9uIHdpbmRvdyBzY3JpcHQgbm8gbG9uZ2VyIGV4aXN0cy4iLCAxNiwgIkZsZWVjZSBUb29scyINCiAgICBXU2NyaXB0LlF1aXQgMw0KRW5kIElmDQoNCnRvb2xEaXIgPSBmc28uR2V0UGFyZW50Rm9sZGVyTmFtZShzY3JpcHRQYXRoKQ0KcHl0aG9udyA9IGZzby5CdWlsZFBhdGgodG9vbERpciwgIi5ydW50aW1lXHB5dGhvblxweXRob253LmV4ZSIpDQpJZiBOb3QgZnNvLkZpbGVFeGlzdHMocHl0aG9udykgVGhlbg0KICAgIHB5dGhvbncgPSBmc28uQnVpbGRQYXRoKHRvb2xEaXIsICIudmVudlxTY3JpcHRzXHB5dGhvbncuZXhlIikNCkVuZCBJZg0KDQpJZiBOb3QgZnNvLkZpbGVFeGlzdHMocHl0aG9udykgVGhlbg0KICAgIE1zZ0JveCAiVGhpcyB0b29sJ3MgcHJpdmF0ZSBQeXRob24gaXMgbWlzc2luZy4gUnVuIEluc3RhbGxlci5iYXQgaW4gdGhlIHNhbWUgZm9sZGVyLCB0aGVuIHRyeSBhZ2Fpbi4iLCAxNiwgIkZsZWVjZSBUb29scyINCiAgICBXU2NyaXB0LlF1aXQgNA0KRW5kIElmDQoNCnNoZWxsLkN1cnJlbnREaXJlY3RvcnkgPSB0b29sRGlyDQpjb21tYW5kTGluZSA9IFF1b3RlQXJndW1lbnQocHl0aG9udykgJiAiIC1JICIgJiBRdW90ZUFyZ3VtZW50KHNjcmlwdFBhdGgpDQpGb3IgaW5kZXggPSAxIFRvIFdTY3JpcHQuQXJndW1lbnRzLkNvdW50IC0gMQ0KICAgIGNvbW1hbmRMaW5lID0gY29tbWFuZExpbmUgJiAiICIgJiBRdW90ZUFyZ3VtZW50KFdTY3JpcHQuQXJndW1lbnRzKGluZGV4KSkNCk5leHQNCg0Kc2hlbGwuUnVuIGNvbW1hbmRMaW5lLCAwLCBGYWxzZQ0KV1NjcmlwdC5RdWl0IDANCg0KRnVuY3Rpb24gUXVvdGVBcmd1bWVudCh2YWx1ZSkNCiAgICBRdW90ZUFyZ3VtZW50ID0gQ2hyKDM0KSAmIFJlcGxhY2UoQ1N0cih2YWx1ZSksIENocigzNCksIENocigzNCkgJiBDaHIoMzQpKSAmIENocigzNCkNCkVuZCBGdW5jdGlvbg0K"
set "ASSOC_RESTORE_B64=QGVjaG8gb2ZmDQpzZXRsb2NhbCBFbmFibGVFeHRlbnNpb25zIERpc2FibGVEZWxheWVkRXhwYW5zaW9uDQpzZXQgIlNIQVJFRF9ESVI9JUxPQ0FMQVBQREFUQSVcRmxlZWNlIFRvb2xzXFB5dGhvbiBMYXVuY2hlciINCiIlU3lzdGVtUm9vdCVcU3lzdGVtMzJcV2luZG93c1Bvd2VyU2hlbGxcdjEuMFxwb3dlcnNoZWxsLmV4ZSIgLU5vTG9nbyAtTm9Qcm9maWxlIC1FeGVjdXRpb25Qb2xpY3kgQnlwYXNzIC1GaWxlICIlU0hBUkVEX0RJUiVcTWFuYWdlLVB5d0Fzc29jaWF0aW9uLnBzMSIgLU1vZGUgUmVzdG9yZSAtTGF1bmNoZXJQYXRoICIlU0hBUkVEX0RJUiVcRmxlZWNlUHl3TGF1bmNoZXIudmJzIiAtRXhwZWN0ZWRMYXVuY2hlclNoYTI1NiAiNDI0MkJCNUQxQjBBMjYxODVBQjJFODE3NjkzQkYxMjgzN0IxQ0U1RTY4RUNEODM5Mzg3NTgwNzNFQTc5NDlCQSINCnNldCAiUkVTVUxUPSVFUlJPUkxFVkVMJSINCmVjaG8uDQppZiAiJVJFU1VMVCUiPT0iMCIgZWNobyBZb3UgbWF5IG5vdyBkZWxldGUgIiVTSEFSRURfRElSJSIgaWYgbm8gRmxlZWNlIFRvb2xzIGluc3RhbGxlcnMgYXJlIHVzaW5nIGl0Lg0KaWYgbm90ICIlUkVTVUxUJSI9PSIwIiBlY2hvIE5vdGhpbmcgd2FzIG92ZXJ3cml0dGVuLiBSZXZpZXcgdGhlIG1lc3NhZ2UgYWJvdmUuDQplY2hvLg0KcGF1c2UNCmV4aXQgL2IgJVJFU1VMVCUNCg=="

set "ASSOC_MANAGER_SHA256=0575C67D732863E4474032D469334C1242721399220EB6DCACB30CC61F16C368"
set "ASSOC_MANAGER_GZIP_B64_1=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"
set "ASSOC_MANAGER_GZIP_B64_2=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"
set "ASSOC_MANAGER_GZIP_B64_3=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"
set "ASSOC_MANAGER_GZIP_B64_4="

set "PYTHON_VERSION=3.14.7"
set "PYSIDE_VERSION=6.11.2"
set "PYSIDE_DISTRIBUTION=PySide6-Essentials"
set "HTTPX_VERSION=0.28.1"
set "PIP_VERSION=26.2.1"
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
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "if([IO.Path]::GetFullPath($env:ROOT).Length -gt [int]$env:MAX_ROOT_LENGTH){exit 2}" >nul 2>nul
if errorlevel 1 (
    set "FAIL_MESSAGE=The complete app folder path must be 72 characters or fewer. Move the extracted folder closer to the drive root and try again."
    goto Failed
)
call :ValidatePrivatePaths
if errorlevel 1 (
    set "FAIL_MESSAGE=The app folder or one of its private setup paths is not safe to modify. Extract a fresh copy to a normal folder and try again."
    goto Failed
)
if "%TEST_ASSOCIATION%"=="1" goto SetupApprovalReady
cls
echo.
echo   The app and private components stay inside this folder.
echo   A small per-user Fleece Tools launcher opens .pyw files.
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
echo  ==================================================
echo.
if "%ASSUME_YES%"=="1" (
    echo   Continue with install or repair? [Y/N]: Y
) else (
    choice /C YN /N /M "  Continue with install or repair? [Y/N]: "
    if errorlevel 2 goto Cancelled
)

:SetupApprovalReady
set "PATHS_VALIDATED=1"
if exist "%RUNTIME%" call :ValidatePrivateTree "%RUNTIME%"
if errorlevel 1 (
    set "FAIL_MESSAGE=The private runtime contains an unsafe link, junction, or path. Extract a fresh copy and try again."
    goto Failed
)
call :ValidateSetupPaths
if errorlevel 2 (
    set "FAIL_MESSAGE=The extracted app folder path is too long for PySide6 on this Windows setup. Move the AI Location Finder folder closer to the drive root, such as C:\Fleece Tools\AI Location Finder, and run setup again."
    goto Failed
)
if errorlevel 1 (
    set "FAIL_MESSAGE=The app folder or one of its private setup folders is not safe to modify. Extract a fresh copy to a normal folder and try again."
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
call :ValidatePrivatePaths
if errorlevel 1 (
    set "FAIL_MESSAGE=The app folder or one of its private setup paths is not safe to modify. Extract a fresh copy to a normal folder and try again."
    goto Failed
)
if exist "%RUNTIME%" call :ValidatePrivateTree "%RUNTIME%"
if errorlevel 1 (
    set "FAIL_MESSAGE=The private runtime contains an unsafe link, junction, or path. Extract a fresh copy and try again."
    goto Failed
)
call :ValidateSetupPaths
if errorlevel 2 (
    set "FAIL_MESSAGE=The extracted app folder path is too long for PySide6 on this Windows setup. Move the AI Location Finder folder closer to the drive root, such as C:\Fleece Tools\AI Location Finder, and run setup again."
    goto Failed
)
if errorlevel 1 (
    set "FAIL_MESSAGE=The app folder or one of its private setup folders is not safe to modify. Extract a fresh copy to a normal folder and try again."
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
if "%TEST_ASSOCIATION%"=="1" goto AssociationTestOnly
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
    if exist "%VENV%" rmdir /s /q "%VENV%" >>"%LOG%" 2>&1
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

if exist "%VENV%" rmdir /s /q "%VENV%" >>"%LOG%" 2>&1
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
if "%SKIP_ASSOCIATION%"=="1" goto AssociationSkipped
echo      Setting the safe Fleece Tools .pyw launcher for this user...
call :InstallPywAssociation
if errorlevel 1 (
    goto AssociationWarning
)
goto AssociationReady

:AssociationWarning
set "ASSOCIATION_WARNING=1"
echo      Warning: direct .pyw opening could not be configured.
echo      The verified start shortcut will still work normally.
set "LOG_MESSAGE=WARNING: The optional shared .pyw launcher could not be installed and verified. The app shortcut remains usable and any previous association backup was kept."
call :LogCurrent
goto AssociationReady

:AssociationSkipped
echo      Internal test mode skipped the Windows .pyw association.

:AssociationReady
call :WriteSetupMarker
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup finished its checks but could not save the completion marker."
    goto Failed
)
echo      Every check passed.

if exist "%DOWNLOADS%" rmdir /s /q "%DOWNLOADS%" >>"%LOG%" 2>&1
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
if "%ASSOCIATION_WARNING%"=="1" (
    echo   Windows did not allow direct .pyw opening to be configured.
    echo   This does not affect the verified start shortcut.
    echo.
) else if not "%SKIP_ASSOCIATION%"=="1" (
    echo   The shared .pyw launcher and restore helper are in:
    echo   "%ASSOCIATION_SHARED_DIR%"
    echo.
)
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

:ValidatePrivatePaths
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$root=[IO.Path]::GetFullPath($env:ROOT).TrimEnd('\');$volume=[IO.Path]::GetPathRoot($root).TrimEnd('\');if([string]::IsNullOrWhiteSpace($root)-or $root -ieq $volume){throw 'Unsafe project root.'};$rootItem=Get-Item -LiteralPath $root -Force;if(-not $rootItem.PSIsContainer-or($rootItem.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'The project root must be a normal directory.'};$targets=@($env:RUNTIME,$env:VENV,$env:DOWNLOADS,$env:PYTHON_DIR,(Join-Path $env:PYTHON_DIR 'Lib'),$env:LOCAL_SITE,$env:SETUP_LOCK,($env:PYTHON_DIR+'.new'),($env:PYTHON_DIR+'.old'),($env:VENV+'.old'),(Join-Path $env:RUNTIME 'environment-before-package-repair'),(Join-Path $env:RUNTIME 'environment-before-package-repair.new'),(Join-Path $env:RUNTIME 'environment-before-package-repair.old'),(Join-Path $env:RUNTIME 'association-test'),(Join-Path $env:RUNTIME 'setup-check'));foreach($name in @('FFMPEG_DIR','DENO_DIR','HERCULES_DIR','LUA_DIR')){$value=[Environment]::GetEnvironmentVariable($name);if($value){$targets+=@($value,($value+'.new'),($value+'.old'),($value+'.extract'))}};$prefix=$root+'\';foreach($target in $targets){if([string]::IsNullOrWhiteSpace($target)){throw 'A private setup path is empty.'};$full=[IO.Path]::GetFullPath($target).TrimEnd('\');if(-not $full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'A private setup path escaped the project root.'};if(Test-Path -LiteralPath $full){$item=Get-Item -LiteralPath $full -Force;if(-not $item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'A private setup directory is unsafe.'}}};foreach($file in @($env:LOG,$env:SETUP_MARKER,($env:SETUP_MARKER+'.new'),$env:SETUP_LOCK_OWNER,($env:SETUP_LOCK_OWNER+'.new'),$env:PIP_WHEEL)){if([string]::IsNullOrWhiteSpace($file)){continue};$full=[IO.Path]::GetFullPath($file);if(-not $full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'A private setup file escaped the project root.'};if(Test-Path -LiteralPath $full){$item=Get-Item -LiteralPath $full -Force;if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'A private setup file is unsafe.'}}};$local=[IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd('\');$association=[IO.Path]::GetFullPath($env:ASSOCIATION_SHARED_DIR).TrimEnd('\');$localItem=Get-Item -LiteralPath $local -Force;if(-not $localItem.PSIsContainer-or($localItem.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'The local app-data root is unsafe.'};$localPrefix=$local+'\';if(-not $association.StartsWith($localPrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'The shared launcher escaped local app data.'};$current=$local;foreach($part in ($association.Substring($localPrefix.Length)-split '\\')){if(-not $part){continue};$current=Join-Path $current $part;if(Test-Path -LiteralPath $current){$item=Get-Item -LiteralPath $current -Force;if(-not $item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'The shared launcher path is unsafe.'}}};exit 0" >nul 2>nul
exit /b %ERRORLEVEL%

:ValidateSetupPaths
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $rootPath=[IO.Path]::GetFullPath($env:ROOT); $root=$rootPath.TrimEnd('\'); $volumeRoot=[IO.Path]::GetPathRoot($rootPath).TrimEnd('\'); $rootWithSeparator=$root+'\'; if([string]::IsNullOrWhiteSpace($root) -or $root -ieq $volumeRoot){throw 'The project root cannot be a drive or share root.'}; foreach($target in @($env:RUNTIME,$env:VENV,$env:DOWNLOADS,$env:PYTHON_DIR,$env:SETUP_LOCK)){if([string]::IsNullOrWhiteSpace($target)){throw 'A setup target path is empty.'}; $full=[IO.Path]::GetFullPath($target).TrimEnd('\'); if(-not $full.StartsWith($rootWithSeparator,[StringComparison]::OrdinalIgnoreCase)){throw ('A setup target escaped the project folder: '+$full)}; if(Test-Path -LiteralPath $full){$item=Get-Item -LiteralPath $full -Force; if(-not $item.PSIsContainer){throw ('A setup folder path is occupied by a file: '+$full)}; if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw ('A private setup folder cannot be a link or junction: '+$full)}}}; exit 0" >>"%DIAGNOSTIC_LOG%" 2>&1
exit /b %ERRORLEVEL%

:WriteSetupMarker
if /I not "%ENV_MODE%"=="venv" if /I not "%ENV_MODE%"=="embedded" exit /b 1
>"%SETUP_MARKER%.new" echo %ENV_MODE%
if errorlevel 1 exit /b 1
move /y "%SETUP_MARKER%.new" "%SETUP_MARKER%" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
if not exist "%SETUP_MARKER%" exit /b 1
exit /b 0

:ReleaseSetupLock
if not "%SETUP_LOCK_HELD%"=="1" exit /b 0
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; if(-not(Test-Path -LiteralPath $env:SETUP_LOCK_OWNER)){exit 2}; $data=Get-Content -LiteralPath $env:SETUP_LOCK_OWNER -Raw -Encoding UTF8|ConvertFrom-Json; if([string]$data.token -ne $env:SETUP_LOCK_TOKEN){exit 2}; $released=$env:SETUP_LOCK+'.released-'+[Guid]::NewGuid().ToString('N'); Move-Item -LiteralPath $env:SETUP_LOCK -Destination $released; Remove-Item -LiteralPath $released -Recurse -Force" >nul 2>nul
set "RELEASE_LOCK_CODE=%ERRORLEVEL%"
set "SETUP_LOCK_HELD=0"
set "SETUP_LOCK_TOKEN="
exit /b %RELEASE_LOCK_CODE%

:TouchSetupLock
if not "%SETUP_LOCK_HELD%"=="1" exit /b 0
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $data=Get-Content -LiteralPath $env:SETUP_LOCK_OWNER -Raw -Encoding UTF8|ConvertFrom-Json; if([string]$data.token -ne $env:SETUP_LOCK_TOKEN){exit 2}; $data.heartbeatUtc=[DateTime]::UtcNow.ToString('o'); $new=$env:SETUP_LOCK_OWNER+'.new'; $data|ConvertTo-Json -Compress|Set-Content -LiteralPath $new -Encoding UTF8; Move-Item -LiteralPath $new -Destination $env:SETUP_LOCK_OWNER -Force" >nul 2>nul
exit /b %ERRORLEVEL%


:FindBasePython
set "BASE_PY="
where py.exe >nul 2>nul
if errorlevel 1 goto FindPathPython
for %%V in (3.14 3.13 3.12 3.11 3.10) do call :TryPyTag %%V
if defined BASE_PY exit /b 0

:FindPathPython
call :TryPythonCommand python.exe
if defined BASE_PY exit /b 0
call :TryPythonCommand python3.exe
if defined BASE_PY exit /b 0
for /f "delims=" %%P in ('where python.exe 2^>nul ^| findstr /V /I /C:"Microsoft\WindowsApps"') do call :TryPythonPath "%%P"
if defined BASE_PY exit /b 0
for /f "delims=" %%P in ('where python3.exe 2^>nul ^| findstr /V /I /C:"Microsoft\WindowsApps"') do call :TryPythonPath "%%P"
if defined BASE_PY exit /b 0

for %%P in (
    "%LocalAppData%\Programs\Python\Python314\python.exe"
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python314\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
) do call :TryPythonPath "%%~fP"
exit /b 0

:TryPythonCommand
if defined BASE_PY exit /b 0
where %~1 >nul 2>nul
if errorlevel 1 exit /b 1
set "CANDIDATE_FILE=%RUNTIME%\python-candidate.txt"
%~1 -I -c "import sys; print(sys.executable)" >"%CANDIDATE_FILE%" 2>>"%LOG%"
if errorlevel 1 exit /b 1
set "CANDIDATE="
set /p "CANDIDATE="<"%CANDIDATE_FILE%"
del /f /q "%CANDIDATE_FILE%" >nul 2>nul
if not defined CANDIDATE exit /b 1
call :TryPythonPath "%CANDIDATE%"
exit /b %ERRORLEVEL%

:TryPyTag
if defined BASE_PY exit /b 0
py -0p 2>nul | findstr /I /C:":%~1" >nul
if errorlevel 1 exit /b 1
set "CANDIDATE_FILE=%RUNTIME%\python-candidate.txt"
py -%~1 -I -c "import sys; print(sys.executable)" >"%CANDIDATE_FILE%" 2>>"%LOG%"
if errorlevel 1 exit /b 1
set "CANDIDATE="
set /p "CANDIDATE="<"%CANDIDATE_FILE%"
del /f /q "%CANDIDATE_FILE%" >nul 2>nul
if not defined CANDIDATE exit /b 1
call :TryPythonPath "%CANDIDATE%"
exit /b %ERRORLEVEL%

:TryPythonPath
if defined BASE_PY exit /b 0
if "%~1"=="" exit /b 1
if not exist "%~1" exit /b 1
call :ValidatePython "%~1"
if errorlevel 1 exit /b 1
set "BASE_PY=%~1"
set "LOG_MESSAGE=Found compatible base CPython: %~1"
call :LogCurrent
exit /b 0

:ValidatePython
if "%~1"=="" exit /b 1
if not exist "%~1" exit /b 1
"%~1" -I -c "import sys, struct, venv, ensurepip; ok = sys.implementation.name == 'cpython' and (3, 10) <= sys.version_info[:2] < (3, 15) and struct.calcsize('P') == 8; raise SystemExit(0 if ok else 1)" >>"%LOG%" 2>&1
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

:DescribePython
"%~1" -I -c "import sys, platform; print('Selected CPython ' + platform.python_version() + ' at ' + sys.executable)" >>"%LOG%" 2>&1
set "PYTHON_VERSION_FILE=%RUNTIME%\python-version.txt"
"%~1" -I -c "import platform; print(platform.python_version())" >"%PYTHON_VERSION_FILE%" 2>>"%LOG%"
set "PYTHON_DISPLAY_VERSION="
if exist "%PYTHON_VERSION_FILE%" set /p "PYTHON_DISPLAY_VERSION="<"%PYTHON_VERSION_FILE%"
del /f /q "%PYTHON_VERSION_FILE%" >nul 2>nul
if defined PYTHON_DISPLAY_VERSION echo      Using compatible Python %PYTHON_DISPLAY_VERSION%.
exit /b 0

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

if exist "%PYTHON_NEW%" rmdir /s /q "%PYTHON_NEW%" >>"%LOG%" 2>&1
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
if /I "%ENV_MODE%"=="venv" goto ValidateSelectedVenv
if /I "%ENV_MODE%"=="embedded" goto ValidateSelectedEmbedded
exit /b 1

:ValidateSelectedVenv
call :ValidateVenv
exit /b %ERRORLEVEL%

:ValidateSelectedEmbedded
call :ValidateEmbeddedPython
exit /b %ERRORLEVEL%

:ValidateVenv
if not exist "%VENV_PY%" exit /b 1
if not exist "%VENV_PYW%" exit /b 1
"%VENV_PY%" -I -c "import sys, struct; ok = sys.implementation.name == 'cpython' and (3, 10) <= sys.version_info[:2] < (3, 15) and struct.calcsize('P') == 8 and sys.prefix != sys.base_prefix; raise SystemExit(0 if ok else 1)" >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:CreateVenv
if not defined BASE_PY exit /b 1
call :ValidatePython "%BASE_PY%"
if errorlevel 1 exit /b 1

if exist "%VENV%" rmdir /s /q "%VENV%" >>"%LOG%" 2>&1
if exist "%VENV%" exit /b 1

set "LOG_MESSAGE=Creating virtual environment with: %BASE_PY%"
call :LogCurrent
"%BASE_PY%" -I -m venv --copies "%VENV%" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
call :ValidateVenv
exit /b %ERRORLEVEL%

:InstallPythonPackages
if not defined APP_PY exit /b 1
if not exist "%APP_PY%" exit /b 1
call :CurrentPackagesFullyHealthy
if not errorlevel 1 exit /b 0
call :BeginPackageTransaction
if errorlevel 1 exit /b 1
if /I "%ENV_MODE%"=="venv" call :InstallVenvPackages
if /I "%ENV_MODE%"=="embedded" call :InstallEmbeddedPackages
set "PACKAGE_TRANSACTION_CODE=%ERRORLEVEL%"
call :FinishPackageTransaction %PACKAGE_TRANSACTION_CODE%
exit /b %ERRORLEVEL%

:CurrentPackagesFullyHealthy
if /I "%ENV_MODE%"=="venv" (
    call :HasPinnedPip
    if errorlevel 1 exit /b 1
)
call :HasPinnedPackages
if errorlevel 1 exit /b 1
call :VerifyPythonPackages
exit /b %ERRORLEVEL%

:BeginPackageTransaction
set "PACKAGE_BACKUP=%RUNTIME%\environment-before-package-repair"
set "PACKAGE_BACKUP_NEW=%PACKAGE_BACKUP%.new"
set "PACKAGE_TARGET="
set "PACKAGE_BACKUP_PROBE="
if /I "%ENV_MODE%"=="venv" set "PACKAGE_TARGET=%VENV%"
if /I "%ENV_MODE%"=="embedded" set "PACKAGE_TARGET=%PYTHON_DIR%"
if /I "%ENV_MODE%"=="venv" set "PACKAGE_BACKUP_PROBE=Scripts\python.exe"
if /I "%ENV_MODE%"=="embedded" set "PACKAGE_BACKUP_PROBE=python.exe"
if not defined PACKAGE_TARGET exit /b 1
if not defined PACKAGE_BACKUP_PROBE exit /b 1
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

:InstallVenvPackages
call :EnsureCurrentVenvPip
if errorlevel 1 exit /b 1
call :HasPinnedPackages
if errorlevel 1 goto CheckVenvPip
call :VerifyPythonPackages
if not errorlevel 1 exit /b 0

:CheckVenvPip
"%APP_PY%" -I -m pip --version >>"%LOG%" 2>&1
if not errorlevel 1 goto InstallPinnedVenvPackage
set "LOG_MESSAGE=pip was missing; attempting ensurepip repair."
call :LogCurrent
"%APP_PY%" -I -m ensurepip --upgrade >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1

:InstallPinnedVenvPackage
set "LOG_MESSAGE=Installing pinned %PYSIDE_DISTRIBUTION% %PYSIDE_VERSION% and httpx %HTTPX_VERSION% from official PyPI."
call :LogCurrent
"%APP_PY%" -I -m pip --isolated --disable-pip-version-check install --upgrade --no-cache-dir --only-binary=:all: --index-url "%PYPI_INDEX%" "%PYSIDE_DISTRIBUTION%==%PYSIDE_VERSION%" "httpx==%HTTPX_VERSION%" >>"%LOG%" 2>&1
set "PACKAGE_INSTALL_CODE=%ERRORLEVEL%"
goto CheckInstalledPackages

:EnsureCurrentVenvPip
call :HasPinnedPip
if not errorlevel 1 exit /b 0
"%APP_PY%" -I -m pip --version >>"%LOG%" 2>&1
if not errorlevel 1 goto UpgradeCurrentVenvPip
set "LOG_MESSAGE=pip was missing; attempting ensurepip repair."
call :LogCurrent
"%APP_PY%" -I -m ensurepip --upgrade >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
:UpgradeCurrentVenvPip
"%APP_PY%" -I -m pip --isolated --disable-pip-version-check install --upgrade --no-cache-dir --only-binary=:all: --index-url "%PYPI_INDEX%" "pip==%PIP_VERSION%" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
"%APP_PY%" -I -c "from importlib.metadata import version; raise SystemExit(0 if version('pip') == '%PIP_VERSION%' else 1)" >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:HasPinnedPip
if not defined APP_PY exit /b 1
if not exist "%APP_PY%" exit /b 1
"%APP_PY%" -I -c "from importlib.metadata import version; raise SystemExit(0 if version('pip') == '%PIP_VERSION%' else 1)" >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:InstallEmbeddedPackages
call :ValidateEmbeddedPython
if errorlevel 1 exit /b 1
call :HasPinnedPackages
if errorlevel 1 goto InstallFullEmbeddedPackages
call :VerifyPythonPackages
if not errorlevel 1 exit /b 0

:InstallFullEmbeddedPackages
set "LOG_MESSAGE=Installing pinned %PYSIDE_DISTRIBUTION% %PYSIDE_VERSION% and httpx %HTTPX_VERSION% into embedded CPython from official PyPI."
call :LogCurrent
call :ResetEmbeddedPackages
if errorlevel 1 exit /b 1
"%APP_PY%" -I -c "import sys; sys.path.insert(0, sys.argv[1]); from pip._internal.cli.main import main; raise SystemExit(main(sys.argv[2:]))" "%PIP_WHEEL%" --isolated --disable-pip-version-check install --upgrade --no-cache-dir --only-binary=:all: --index-url "%PYPI_INDEX%" --target "%LOCAL_SITE%" "%PYSIDE_DISTRIBUTION%==%PYSIDE_VERSION%" "httpx==%HTTPX_VERSION%" >>"%LOG%" 2>&1
set "PACKAGE_INSTALL_CODE=%ERRORLEVEL%"

:CheckInstalledPackages
if not "%PACKAGE_INSTALL_CODE%"=="0" goto RepairPythonPackages
call :VerifyPythonPackages
if not errorlevel 1 exit /b 0

:RepairPythonPackages
echo      A component check failed. Repairing local packages...
set "LOG_MESSAGE=Initial package validation failed; forcing a clean package reinstall."
call :LogCurrent
if /I "%ENV_MODE%"=="venv" goto RepairVenvPackages
if /I "%ENV_MODE%"=="embedded" goto RepairEmbeddedPackages
exit /b 1

:RepairVenvPackages
"%APP_PY%" -I -m pip --isolated --disable-pip-version-check install --upgrade --force-reinstall --no-cache-dir --only-binary=:all: --index-url "%PYPI_INDEX%" "%PYSIDE_DISTRIBUTION%==%PYSIDE_VERSION%" "httpx==%HTTPX_VERSION%" >>"%LOG%" 2>&1
goto RepairPackagesFinished

:RepairEmbeddedPackages
call :ResetEmbeddedPackages
if errorlevel 1 exit /b 1
"%APP_PY%" -I -c "import sys; sys.path.insert(0, sys.argv[1]); from pip._internal.cli.main import main; raise SystemExit(main(sys.argv[2:]))" "%PIP_WHEEL%" --isolated --disable-pip-version-check install --upgrade --force-reinstall --no-cache-dir --only-binary=:all: --index-url "%PYPI_INDEX%" --target "%LOCAL_SITE%" "%PYSIDE_DISTRIBUTION%==%PYSIDE_VERSION%" "httpx==%HTTPX_VERSION%" >>"%LOG%" 2>&1

:RepairPackagesFinished
if errorlevel 1 exit /b 1
call :VerifyPythonPackages
exit /b %ERRORLEVEL%

:VerifyPythonPackages
if not defined APP_PY exit /b 1
if not exist "%APP_PY%" exit /b 1
"%APP_PY%" -I -c "import httpx, PySide6; from importlib.metadata import version; from PySide6.QtCore import qVersion; from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache; assert version('%PYSIDE_DISTRIBUTION%') == '%PYSIDE_VERSION%'; assert version('httpx') == '%HTTPX_VERSION%'; assert hasattr(httpx, 'Client') and hasattr(httpx, 'AsyncClient'); assert QNetworkAccessManager and QNetworkDiskCache; print('%PYSIDE_DISTRIBUTION%=' + version('%PYSIDE_DISTRIBUTION%')); print('httpx=' + version('httpx')); print('Qt=' + qVersion())" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
if /I "%ENV_MODE%"=="venv" goto CheckVenvDependencies
if /I "%ENV_MODE%"=="embedded" goto CheckEmbeddedDependencies
exit /b 1

:CheckVenvDependencies
"%APP_PY%" -I -m pip --isolated --disable-pip-version-check check >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:CheckEmbeddedDependencies
"%APP_PY%" -I -c "import sys; sys.path.insert(0, sys.argv[1]); from pip._internal.cli.main import main; raise SystemExit(main(sys.argv[2:]))" "%PIP_WHEEL%" --isolated --disable-pip-version-check check >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:HasPinnedPackages
if not defined APP_PY exit /b 1
if not exist "%APP_PY%" exit /b 1
"%APP_PY%" -I -c "import httpx, PySide6; from importlib.metadata import version; from PySide6.QtNetwork import QNetworkAccessManager; ok = version('%PYSIDE_DISTRIBUTION%') == '%PYSIDE_VERSION%' and version('httpx') == '%HTTPX_VERSION%' and bool(QNetworkAccessManager); raise SystemExit(0 if ok else 1)" >>"%LOG%" 2>&1
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
if exist "%REPLACE_TARGET%" call :ValidatePrivateTree "%REPLACE_TARGET%"
if errorlevel 1 exit /b 1
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
if exist "%REPLACE_BACKUP%" call :RemoveDirectoryRobust "%REPLACE_BACKUP%"
if errorlevel 1 exit /b 1
if exist "%REPLACE_BACKUP%" exit /b 1
exit /b 0

:ReplaceRollback
if exist "%REPLACE_TARGET%" call :RemoveDirectoryRobust "%REPLACE_TARGET%"
if errorlevel 1 exit /b 1
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
if exist "%CHECK_DIR%" rmdir /s /q "%CHECK_DIR%" >>"%LOG%" 2>&1
mkdir "%CHECK_DIR%" >>"%LOG%" 2>&1
if not exist "%CHECK_DIR%" exit /b 1
set "APP_CHECK_CODE=0"
"%APP_PY%" -I "%APP_FILE%" --install-check "%CHECK_DIR%" >>"%LOG%" 2>&1
if errorlevel 1 set "APP_CHECK_CODE=1"
if not "%APP_CHECK_CODE%"=="0" goto AppCheckCleanup
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $items=@(Get-ChildItem -LiteralPath $env:CHECK_DIR -Force); if($items.Count -ne 1){throw 'Install check must create exactly one result file.'}; $item=$items[0]; if($item.PSIsContainer -or $item.Name -cne 'checks.json'){throw 'Install check did not create only checks.json.'}; $data=Get-Content -LiteralPath $item.FullName -Raw | ConvertFrom-Json; if($null -eq $data){throw 'checks.json did not contain a JSON result.'}; foreach($name in @('passed','app','version','network_requests','real_desktop_captures','providers','model_entries','checks')){if($data.PSObject.Properties.Name -notcontains $name){throw ('checks.json is missing ' + $name)}}; if($data.passed -isnot [bool] -or -not $data.passed){throw 'App install check did not pass.'}; if($data.app -isnot [string] -or $data.app -cne 'AI Location Finder'){throw 'checks.json reported the wrong app.'}; if($data.version -isnot [string] -or $data.version -cne '1.0.5'){throw 'checks.json reported the wrong app version.'}; foreach($name in @('network_requests','real_desktop_captures','providers','model_entries')){if($data.$name -isnot [int] -and $data.$name -isnot [long]){throw ('checks.json has a non-integer ' + $name)}}; if($data.network_requests -ne 0 -or $data.real_desktop_captures -ne 0){throw 'App install check used network requests or desktop capture.'}; if($data.providers -ne 4){throw 'App install check reported the wrong provider count.'}; if($data.model_entries -lt 1){throw 'App install check did not report any models.'}; if($data.checks -isnot [System.Array]){throw 'App install checks must be an array.'}; $checks=@($data.checks); if($checks.Count -ne 6){throw 'App install check did not complete the expected checks.'}; foreach($check in $checks){if($check -isnot [string] -or [string]::IsNullOrWhiteSpace($check)){throw 'App install check contained an empty check.'}}; Write-Output 'Safe app install-check output verified.'" >>"%LOG%" 2>&1
if errorlevel 1 set "APP_CHECK_CODE=1"

:AppCheckCleanup
rmdir /s /q "%CHECK_DIR%" >>"%LOG%" 2>&1
if exist "%CHECK_DIR%" exit /b 1
if not "%APP_CHECK_CODE%"=="0" exit /b 1
exit /b 0

:SetAssociationPaths
if not defined ASSOCIATION_DIR exit /b 1
set "ASSOCIATION_LAUNCHER=%ASSOCIATION_DIR%\FleecePywLauncher.vbs"
set "ASSOCIATION_MANAGER=%ASSOCIATION_DIR%\Manage-PywAssociation.ps1"
set "ASSOCIATION_RESTORE=%ASSOCIATION_DIR%\Restore pyw association.cmd"
exit /b 0

:WriteAssociationAssets
if not defined ASSOCIATION_DIR exit /b 1
call :SetAssociationPaths
if errorlevel 1 exit /b 1
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';function Get-Hash([byte[]]$bytes){$sha=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','')}finally{$sha.Dispose()}};function Save-Checked([string]$path,[byte[]]$bytes,[string]$expected){if((Get-Hash $bytes) -cne $expected){throw ('Embedded asset hash mismatch for '+$path)};if(Test-Path -LiteralPath $path){$item=Get-Item -LiteralPath $path -Force;if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw ('Association asset target is not a regular file: '+$path)}};$candidate=$path+'.new.'+[Guid]::NewGuid().ToString('N');try{[IO.File]::WriteAllBytes($candidate,$bytes);if((Get-Hash ([IO.File]::ReadAllBytes($candidate))) -cne $expected){throw ('Written asset hash mismatch for '+$path)};Move-Item -LiteralPath $candidate -Destination $path -Force;if((Get-Hash ([IO.File]::ReadAllBytes($path))) -cne $expected){throw ('Final asset hash mismatch for '+$path)}}finally{Remove-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue}};New-Item -ItemType Directory -Path $env:ASSOCIATION_DIR -Force|Out-Null;$dir=Get-Item -LiteralPath $env:ASSOCIATION_DIR -Force;if(($dir.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Association asset directory may not be a reparse point'};$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;$mutexName='Global\FleeceTools.PywAssociation.'+($sid -replace '[^A-Za-z0-9_.-]','_');$mutex=New-Object Threading.Mutex($false,$mutexName);$held=$false;$lock=$null;try{try{$held=$mutex.WaitOne([TimeSpan]::FromMinutes(2))}catch [Threading.AbandonedMutexException]{$held=$true};if(-not $held){throw 'Another cross-session association operation is running'};$lockPath=Join-Path $env:ASSOCIATION_DIR 'association-operation.lock';if(Test-Path -LiteralPath $lockPath){$lockItem=Get-Item -LiteralPath $lockPath -Force;if($lockItem.PSIsContainer -or ($lockItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Association operation lock is not a regular file'}};$lock=[IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::Read,[IO.FileShare]::None);foreach($path in @($env:ASSOCIATION_LAUNCHER,$env:ASSOCIATION_MANAGER,$env:ASSOCIATION_RESTORE)){foreach($item in @(Get-ChildItem -LiteralPath $env:ASSOCIATION_DIR -Filter (([IO.Path]::GetFileName($path))+'.new.*') -File -Force -ErrorAction SilentlyContinue)){if($item.Name -match '\.new\.[a-f0-9]{32}$'){Remove-Item -LiteralPath $item.FullName -Force -ErrorAction SilentlyContinue}}};$launcher=[Convert]::FromBase64String($env:ASSOC_LAUNCHER_B64);$restore=[Convert]::FromBase64String($env:ASSOC_RESTORE_B64);$payload=$env:ASSOC_MANAGER_GZIP_B64_1+$env:ASSOC_MANAGER_GZIP_B64_2+$env:ASSOC_MANAGER_GZIP_B64_3+$env:ASSOC_MANAGER_GZIP_B64_4;$compressed=[Convert]::FromBase64String($payload);$input=[IO.MemoryStream]::new($compressed);$gzip=[IO.Compression.GZipStream]::new($input,[IO.Compression.CompressionMode]::Decompress);$output=[IO.MemoryStream]::new();try{$gzip.CopyTo($output);$manager=$output.ToArray()}finally{$output.Dispose();$gzip.Dispose();$input.Dispose()};Save-Checked $env:ASSOCIATION_LAUNCHER $launcher $env:ASSOC_LAUNCHER_SHA256;Save-Checked $env:ASSOCIATION_MANAGER $manager $env:ASSOC_MANAGER_SHA256;Save-Checked $env:ASSOCIATION_RESTORE $restore $env:ASSOC_RESTORE_SHA256}finally{if($lock){$lock.Dispose()};if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
if not exist "%ASSOCIATION_LAUNCHER%" exit /b 1
if not exist "%ASSOCIATION_MANAGER%" exit /b 1
if not exist "%ASSOCIATION_RESTORE%" exit /b 1
exit /b 0

:RunAssociationSelfTest
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$errors=$null;$tokens=$null;[Management.Automation.Language.Parser]::ParseFile($env:ASSOCIATION_MANAGER,[ref]$tokens,[ref]$errors)|Out-Null;if($errors){throw ($errors|Out-String)}" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%ASSOCIATION_MANAGER%" -Mode SelfTest -LauncherPath "%ASSOCIATION_LAUNCHER%" -ExpectedLauncherSha256 "%ASSOC_LAUNCHER_SHA256%" >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:RunAssociationTransactionalTest
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$id=[Guid]::NewGuid().ToString('N');$extension='.fzaudit_'+$id;$progId='FleeceTools.Audit.'+$id;$extensionPath='Registry::HKEY_CURRENT_USER\Software\Classes\'+$extension;$progPath='Registry::HKEY_CURRENT_USER\Software\Classes\'+$progId;$explorerPath='Registry::HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\'+$extension;$env:FLEECE_ASSOCIATION_TEST_MODE='1';$failed=$false;try{& $env:ASSOCIATION_MANAGER -Mode Install -LauncherPath $env:ASSOCIATION_LAUNCHER -ExpectedLauncherSha256 $env:ASSOC_LAUNCHER_SHA256 -TestId $id;& $env:ASSOCIATION_MANAGER -Mode Install -LauncherPath $env:ASSOCIATION_LAUNCHER -ExpectedLauncherSha256 $env:ASSOC_LAUNCHER_SHA256 -TestId $id;& $env:ASSOCIATION_MANAGER -Mode Restore -LauncherPath $env:ASSOCIATION_LAUNCHER -ExpectedLauncherSha256 $env:ASSOC_LAUNCHER_SHA256 -TestId $id;if((Test-Path -LiteralPath $extensionPath) -or (Test-Path -LiteralPath $progPath) -or (Test-Path -LiteralPath $explorerPath)){throw 'Disposable association registry cleanup failed'};if(Test-Path -LiteralPath (Join-Path $env:ASSOCIATION_DIR '.association-transaction-v2')){throw 'Disposable association transaction residue remained'};if(Test-Path -LiteralPath (Join-Path $env:ASSOCIATION_DIR 'association-state.json')){throw 'Disposable association state residue remained'};if(@(Get-ChildItem -LiteralPath $env:ASSOCIATION_DIR -Filter '*.new.*' -Force -ErrorAction SilentlyContinue).Count -ne 0){throw 'Disposable association candidate residue remained'}}catch{Write-Error $_;$failed=$true}finally{Remove-Item Env:FLEECE_ASSOCIATION_TEST_MODE -ErrorAction SilentlyContinue;foreach($path in @($extensionPath,$progPath,$explorerPath)){if($path -match [regex]::Escape($id)){Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue}}};if($failed){exit 1};exit 0" >>"%LOG%" 2>&1
exit /b %ERRORLEVEL%

:InstallPywAssociation
set "ASSOCIATION_DIR=%ASSOCIATION_SHARED_DIR%"
call :WriteAssociationAssets
if errorlevel 1 exit /b 1
call :RunAssociationSelfTest
if errorlevel 1 exit /b 1
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%ASSOCIATION_MANAGER%" -Mode Install -LauncherPath "%ASSOCIATION_LAUNCHER%" -ExpectedLauncherSha256 "%ASSOC_LAUNCHER_SHA256%" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
set "LOG_MESSAGE=Installed and validated the shared per-user Fleece Tools .pyw launcher at %ASSOCIATION_DIR%."
call :LogCurrent
exit /b 0

:AssociationTestOnly
set "ASSOCIATION_DIR=%RUNTIME%\association-test"
if exist "%ASSOCIATION_DIR%" rmdir /s /q "%ASSOCIATION_DIR%" >nul 2>nul
set "LOG_MESSAGE=Association offline test root: %ROOT%"
call :LogCurrent
if errorlevel 1 goto AssociationTestFailed
call :WriteAssociationAssets
if errorlevel 1 goto AssociationTestFailed
call :RunAssociationSelfTest
set "ASSOCIATION_TEST_CODE=%ERRORLEVEL%"
if "%ASSOCIATION_TEST_CODE%"=="0" call :RunAssociationTransactionalTest
if errorlevel 1 set "ASSOCIATION_TEST_CODE=1"
if exist "%ASSOCIATION_DIR%" rmdir /s /q "%ASSOCIATION_DIR%" >nul 2>nul
if not "%ASSOCIATION_TEST_CODE%"=="0" goto AssociationTestFailed
call :ReleaseSetupLock
if errorlevel 1 goto AssociationTestFailed
echo Shared .pyw launcher offline checks passed. No association was changed.
exit /b 0

:AssociationTestFailed
if exist "%ASSOCIATION_DIR%" rmdir /s /q "%ASSOCIATION_DIR%" >nul 2>nul
call :ReleaseSetupLock
echo Shared .pyw launcher offline checks failed. No association was changed.
exit /b 1

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
