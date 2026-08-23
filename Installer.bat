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
set "ASSOC_LAUNCHER_SHA256=E0CD6964B4A0EA2384F02A8225A1387191A1B099B1357538A4F02F23FB853C5F"
set "ASSOC_RESTORE_SHA256=F25CFD12B724466A1A7C6DEA7F45866ED77C28712F7462DE05610D7A110297DA"
set "ASSOC_LAUNCHER_B64=T3B0aW9uIEV4cGxpY2l0DQoNCkRpbSBzaGVsbCwgZnNvLCBzY3JpcHRQYXRoLCB0b29sRGlyLCBweXRob253LCBjb21tYW5kTGluZSwgaW5kZXgNClNldCBzaGVsbCA9IENyZWF0ZU9iamVjdCgiV1NjcmlwdC5TaGVsbCIpDQpTZXQgZnNvID0gQ3JlYXRlT2JqZWN0KCJTY3JpcHRpbmcuRmlsZVN5c3RlbU9iamVjdCIpDQoNCklmIFdTY3JpcHQuQXJndW1lbnRzLkNvdW50IDwgMSBUaGVuIFdTY3JpcHQuUXVpdCAyDQoNCnNjcmlwdFBhdGggPSBmc28uR2V0QWJzb2x1dGVQYXRoTmFtZShXU2NyaXB0LkFyZ3VtZW50cygwKSkNCklmIE5vdCBmc28uRmlsZUV4aXN0cyhzY3JpcHRQYXRoKSBUaGVuDQogICAgTXNnQm94ICJUaGUgc2VsZWN0ZWQgUHl0aG9uIHdpbmRvdyBzY3JpcHQgbm8gbG9uZ2VyIGV4aXN0cy4iLCAxNiwgIkZsZWVjZSBUb29scyINCiAgICBXU2NyaXB0LlF1aXQgMw0KRW5kIElmDQoNCnRvb2xEaXIgPSBmc28uR2V0UGFyZW50Rm9sZGVyTmFtZShzY3JpcHRQYXRoKQ0KcHl0aG9udyA9IGZzby5CdWlsZFBhdGgodG9vbERpciwgIi5ydW50aW1lXHB5dGhvblxweXRob253LmV4ZSIpDQpJZiBOb3QgZnNvLkZpbGVFeGlzdHMocHl0aG9udykgVGhlbg0KICAgIHB5dGhvbncgPSBmc28uQnVpbGRQYXRoKHRvb2xEaXIsICIudmVudlxTY3JpcHRzXHB5dGhvbncuZXhlIikNCkVuZCBJZg0KDQpJZiBOb3QgZnNvLkZpbGVFeGlzdHMocHl0aG9udykgVGhlbg0KICAgIE1zZ0JveCAiVGhpcyB0b29sJ3MgcHJpdmF0ZSBQeXRob24gaXMgbWlzc2luZy4gUnVuIEluc3RhbGxlci5iYXQgaW4gdGhlIHNhbWUgZm9sZGVyLCB0aGVuIHRyeSBhZ2Fpbi4iLCAxNiwgIkZsZWVjZSBUb29scyINCiAgICBXU2NyaXB0LlF1aXQgNA0KRW5kIElmDQoNCnNoZWxsLkN1cnJlbnREaXJlY3RvcnkgPSB0b29sRGlyDQpjb21tYW5kTGluZSA9IFF1b3RlQXJndW1lbnQocHl0aG9udykgJiAiICIgJiBRdW90ZUFyZ3VtZW50KHNjcmlwdFBhdGgpDQpGb3IgaW5kZXggPSAxIFRvIFdTY3JpcHQuQXJndW1lbnRzLkNvdW50IC0gMQ0KICAgIGNvbW1hbmRMaW5lID0gY29tbWFuZExpbmUgJiAiICIgJiBRdW90ZUFyZ3VtZW50KFdTY3JpcHQuQXJndW1lbnRzKGluZGV4KSkNCk5leHQNCg0Kc2hlbGwuUnVuIGNvbW1hbmRMaW5lLCAwLCBGYWxzZQ0KV1NjcmlwdC5RdWl0IDANCg0KRnVuY3Rpb24gUXVvdGVBcmd1bWVudCh2YWx1ZSkNCiAgICBRdW90ZUFyZ3VtZW50ID0gQ2hyKDM0KSAmIFJlcGxhY2UoQ1N0cih2YWx1ZSksIENocigzNCksIENocigzNCkgJiBDaHIoMzQpKSAmIENocigzNCkNCkVuZCBGdW5jdGlvbg0K"
set "ASSOC_RESTORE_B64=QGVjaG8gb2ZmDQpzZXRsb2NhbCBFbmFibGVFeHRlbnNpb25zIERpc2FibGVEZWxheWVkRXhwYW5zaW9uDQpzZXQgIlNIQVJFRF9ESVI9JUxPQ0FMQVBQREFUQSVcRmxlZWNlIFRvb2xzXFB5dGhvbiBMYXVuY2hlciINCiIlU3lzdGVtUm9vdCVcU3lzdGVtMzJcV2luZG93c1Bvd2VyU2hlbGxcdjEuMFxwb3dlcnNoZWxsLmV4ZSIgLU5vTG9nbyAtTm9Qcm9maWxlIC1FeGVjdXRpb25Qb2xpY3kgQnlwYXNzIC1GaWxlICIlU0hBUkVEX0RJUiVcTWFuYWdlLVB5d0Fzc29jaWF0aW9uLnBzMSIgLU1vZGUgUmVzdG9yZSAtTGF1bmNoZXJQYXRoICIlU0hBUkVEX0RJUiVcRmxlZWNlUHl3TGF1bmNoZXIudmJzIiAtRXhwZWN0ZWRMYXVuY2hlclNoYTI1NiAiRTBDRDY5NjRCNEEwRUEyMzg0RjAyQTgyMjVBMTM4NzE5MUExQjA5OUIxMzU3NTM4QTRGMDJGMjNGQjg1M0M1RiINCnNldCAiUkVTVUxUPSVFUlJPUkxFVkVMJSINCmVjaG8uDQppZiAiJVJFU1VMVCUiPT0iMCIgZWNobyBZb3UgbWF5IG5vdyBkZWxldGUgIiVTSEFSRURfRElSJSIgaWYgbm8gRmxlZWNlIFRvb2xzIGluc3RhbGxlcnMgYXJlIHVzaW5nIGl0Lg0KaWYgbm90ICIlUkVTVUxUJSI9PSIwIiBlY2hvIE5vdGhpbmcgd2FzIG92ZXJ3cml0dGVuLiBSZXZpZXcgdGhlIG1lc3NhZ2UgYWJvdmUuDQplY2hvLg0KcGF1c2UNCmV4aXQgL2IgJVJFU1VMVCUNCg=="

set "ASSOC_MANAGER_SHA256=74A37F315D1D89C9DD3B0C5607B6395D191FF1236F685AD6CDD19144392FADCF"
set "ASSOC_MANAGER_GZIP_B64_1=H4sIAAAAAAAACrVa62/bOBL/HiD/w8DwnuzbStd2H7gzEOCyjtNkt3kgTrZ3iLMLVhrb3MqkjqTs+Nr+7wc+JFOy5DjtXj7EtsQZDuf5m5EyIsiid3gAAHD/K0lpQhSOUfWCcyYVSdPgBQQ3KBUXqL+OMZ3eolRB/8ERSSUomz10L3iCLw4PalffkpzFcxTXRM03d4uNrolSKFgv+O3+ODwl4fRl+I+Hjz9+/7m7zX/0mGGsMCk4jufk9Q8/Hh70NdfuSAgujmNFObsWOEWBLEY4gmCseBYcHoxRhWMlaKy0nBD+ikJSzuC7wwM6hV7IuAJzBAi5APvTl9273CxIHz6Cmgu+gsBoAionB8ISaCYEIhAE/ienApMogM/mPNMUMcZrwWfniT7Gqfl9y3kqo+u1mnP2jrKEr8axoJkKDg+6cUqkRDl6VMjM0Y604WZUKrEeDM5+Gf379+Hdzc3o8vb3u/HoZjLmU7UiAidDSziJsvXKY1Tu3XkWl4rkncODLj5mKRconi/YBY0Fl3yqJvascjLMhUCmnPEmI8d6ckpTHD2qzRlyiWI459T4QGdbhslduUDLKOdEYHJCBRzB/flVpG32MBi8QXVCBcaKi/UlWWCveu80T1P9q1fxlH5fM1TWu+dwBD9zykLz3dsnIFLymBLtsKFZHf0hOfP0/xOJP+TZXvTvccoFhlbzoaOPBM40u+LsX8yvYFAwFDgbPWKVEbLlYLyWChc3nCsI7PfvXk8EziJ8RE23ksZX96d1BI7+8GCaMxPg8AZVeIJTkqfqV5LmCB9trshMMru/1h+oUPQuCEuIth4cQVeJHPsPZT4xtrJ0ZQbo6dRmxQrfUoWCGAODXaxDXKDKBYMuy9NUh6omd9d6WqxzhYsm2ugNWll7"
set "ASSOC_MANAGER_GZIP_B64_2=QfDCkr+A+9LDo3eUffc6KsLCrLzK9GHlw2Bwwi+5Gj1mhCUjtqSCswUypT1S9g8PPld0M3rMuFBhwekXXFe1Y7+bzLqfni6Jokvjyy+eTXuCUlFmnMrSOoV3FS4yLogh6vjLIoarjl10gwu+xCaNbqjDUy5ihNBL/zCmKTKVroecKcpytNz+AoXjotEQeAfzOf5tDZ/gKlfhZZ6mG/fovj0e347+dX47vDoZQcgQXm5KQqvblGz7ZnGbh2yWRW+RzTSbVMHrl/3CdPrPFpfOkOdpAnpXSaaYruE9iT9AnvnnieCSgxfQEM8Jm6GEFQqEBUkwcjp2HnzxtKI9G4FvMGeCuhueL3a74Z4ONOa5iLFfNyE13MHd3tdgmxLtaVFYbANqrquwldboNM8GxQYdrafq+W6QJOFY5+3iXE8nkbIotGYSuwSOTIbT/otMtTGB8IasIByxmCeUzeDu9vTv8AmGnC1RqFPBF+HPsog7oxFbZmQ8xwUxGnllvNJd5yuG2p+xABtg0EbQ4ITB7RxBkiUmFS+zWgN7BiqdemM+Y/S/mESgqfCRateZVQhXREKKUwW6impPTaKg4p+FrgzruineCaqwaou9fIy//wNj9dA1lM2JqVS2l5bs+o2mb7nRs46QTM3he/gE41breQFVMdyXhaHnC41BaByxwCb7+2kV9+r/t+sM4S2SqfFc3wkMgADfYSAtNqQSFlRKymYW1joPF0gWDmdp3PYwGFxlyHRA1YCUpdDx6HmgxiyaeoxxLqhaR0OxzhSfCZLN19H47Pj1Dz8+DAZDgURhz/Eo+UCXxConKRxB7/4nqpwNUTwMBrdcNwhs1tNbREO+yHKFZ0TOe07ofr8f3WCWkhh7Qai7oaAPn2FKGUlTw1wTnlCZcYm9"
set "ASSOC_MANAGER_GZIP_B64_3=fnHk6grDaXuRCVAnm47Bli4juuV3WYbinC2JoISp3rMsklCb9DIiJVAlgTKFM61GiOcYf/DspPBR7UxEVS+5IStHKHKm6ALPWYKPJtrwUUXm19W0F0Tu9iQzTYz7WBmM9wLurQW07omgkjPtHCLR6jufMS5wSGQZqktky7Zd9L2J7Y3kV+xhrFI5kC7MtvJ7+4cp1s5tFhgV6lBbEBXPIZBzTNNJdJOz9qRqrdduMD6dppQhvMc5WVIuCruV6bIhA7hOHpNjL+e6/XV7YPxsyBcL3aQeQdAJ4Fvw4fq3EHTAXq1Y3V7/5lUHvvlrsNFYbwufO6Rfb1H71tX9jrHmzbqfAyw7R1eg7QkK3SzdMGHjvLuE6FT724k1Cs+QTWKrgo4Tq6aZJslKOznSJ2RqS7ibbrXiF9246GBL4HgteIZCrVsZQKjbAnDN+05c3I/sqs2Gxt3dpqE+Tvljh5lcbw4fMFNAIKFTM31RGmenNKbKqiqxprAoIBO4pDyX4PgLXBDKpEEQmECebfS25dLOm8MGZ67UO3vpEleuour/po6VLT1sdcGunajjyRKWbVCfuxHbgYRLlPv4vCNcEVmGpc5fdgej9AKoXY+vDEKJnNEpysgYN4w5U0ZfgbVJyelOxUHfmc4y2V5QDOE2kLCwtTtL7Vfd9IWQlROYfOeTlAjeilEY3E2JnBO1ZUHjMHWA6JAhkKlCUa1vUyqkgpizKZ3lOn9SFWkQlmcWVmpsz3Cl49T6WxPOrKEjK3gtHgtbUqmM2doCutnoRb51o6inmGwNreqBWpFGR2RD7x96XW5w9svwrmXuV0OW1RnU59rOtTM8f+svnezVpKyNtjwx/Z7AffzTs6T+c33QEbyqXrd90FGtC6quiQ261NGkoegJUXhL"
set "ASSOC_MANAGER_GZIP_B64_4=FxrJ3qn4kq+iEkoGPOjXSGuusfGDmkF3k5XTvBZXqE0qaYpmgFk1rEavmErUwNRvQ4u/LQ/0hK35wBOEVXEb/KdN3qqJnxK4Mc0Y1Vr32qz2CFuzeyUpPLN2tw+v/Fp9o5sYiWX75kfZXhvWi/DKm2ukSCQa0FiW22pJtsnQVmTXu+tEaws5S0CaDCoVzzJM3LipUpjrJbaS/Ipq0VxSdYvcoJwara2kgX3gAStzSLC4FEJoCNCaLHuAvdaaH/85gLj5oHsJZk9fCLJT2ZuHK1+kb4/cbepXfA9cNbUSFYz0CY6TJLzAxXs9TLKfBnVdcoUb9GpwzDY2KbbvPZVT+5WQacj2zaMi9yCzCTu2ZoFtRFAE3SWvwhATVJUhmA6nKc9Zoieyaq6nPR6U8brtL8aRZYuwf8r4vzYTLQnadGT7Ikw3LN+zE2kCkccO7jHOQmciL+PpwRSJNTaJCo8os9yKqjnPFfAlipWgZlRJ1RZMLMzhBtBH9rSbltrUrKab3iC2BQk0Qs6SVePDu14NbTeDBQ+IPD0DrOy7NWMyo19XZJtGwN7kb7fj+9MvK3sb5qiqZUvFe+mlBZY8SzHVnZs1U6DXr1XNU8/BtrN3FVDs81zsSe5F9P+ZrLffCXgm+y8KpoZnUqFzoKq/f5Vv7tql6jz1nOIeRSW1Rw/F5bC7uyyu1+v1xUWShGdni4WUQb9vXino7H624D1DqPRWpTDbhfaMS7WjUS8pFS/QZ1ipk1aZwfZgZ8k/YFi8YbRjqKNNUm0YSovUHiHY51nR8r15jlVEavlIZDNZNGNUmBKa+jFobF8dfmzGub957+RMIp//tV57YjtJOadZC3dfm+Pa4FfXPF+xC8LIDEU5/zUcpZkL2ymG0aVcUS1az7zJVHpl+SoXfGycnjlxyte84GMjUCqWla+AGXZVm9lp3f8A1DUbnFUmAAA="

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
echo  ==================================================
echo                  AI LOCATION FINDER SETUP
echo  ==================================================
echo.
if "%ASSUME_YES%"=="1" (
    echo   Install or repair AI Location Finder in this folder? [Y/N]: Y
) else (
    choice /C YN /N /M "  Install or repair AI Location Finder in this folder? [Y/N]: "
    if errorlevel 2 goto Cancelled
)

:SetupApprovalReady
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
if not exist "%RUNTIME%" mkdir "%RUNTIME%" >>"%LOG%" 2>&1
if not exist "%RUNTIME%" (
    set "FAIL_MESSAGE=Could not create the private runtime folder."
    goto Failed
)
if "%TEST_ASSOCIATION%"=="1" goto AssociationTestOnly
call :AcquireSetupLock
if errorlevel 1 goto SetupAlreadyRunning
call :TouchSetupLock
if errorlevel 1 (
    set "FAIL_MESSAGE=Setup lost ownership of its private setup lock."
    goto Failed
)
call :EnsureAppClosed
if errorlevel 1 (
    set "FAIL_MESSAGE=AI Location Finder is open. Close the app before installing or repairing its files."
    goto Failed
)
if exist "%SETUP_MARKER%" del /f /q "%SETUP_MARKER%" >nul 2>nul
if exist "%SETUP_MARKER%" (
    set "FAIL_MESSAGE=The old setup completion marker could not be cleared."
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

cls
echo.
echo  ==================================================
echo                  AI LOCATION FINDER SETUP
echo  ==================================================
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
    set "FAIL_MESSAGE=The shared .pyw launcher could not be installed and verified. Any previous association backup was kept."
    goto Failed
)
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
if not "%SKIP_ASSOCIATION%"=="1" (
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
if defined PATHS_VALIDATED call :LogCurrent
if defined PATHS_VALIDATED call :ReleaseSetupLock
echo.
echo  ==================================================
echo                     SETUP STOPPED
echo  ==================================================
echo.
echo   %FAIL_MESSAGE%
echo.
echo   No success was reported because all checks did not pass.
if defined PATHS_VALIDATED (
    echo   The detailed log is here:
    echo.
    echo   "%LOG%"
) else (
    echo   No log was written because the private setup paths were not trusted.
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
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $self=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID); if(-not $self -or -not $self.ParentProcessId){throw 'Could not identify the setup process.'}; $parent=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $self.ParentProcessId); if(-not $parent){throw 'Could not identify the setup process.'}; if($env:SETUP_CHILD -ne '1' -or [string]$parent.CommandLine -notmatch '(?i)--fleece-setup-child(?:\s|$)'){throw 'Could not verify the dedicated setup child.'}; $started=([DateTime]$parent.CreationDate).ToUniversalTime().ToString('o'); $data=[ordered]@{schema=2;pid=[int]$parent.ProcessId;processStartedUtc=$started;token=$env:SETUP_LOCK_TOKEN;heartbeatUtc=[DateTime]::UtcNow.ToString('o');child=$true}; $new=$env:SETUP_LOCK_OWNER+'.new'; $data|ConvertTo-Json -Compress|Set-Content -LiteralPath $new -Encoding UTF8; Move-Item -LiteralPath $new -Destination $env:SETUP_LOCK_OWNER -Force" >>"%LOG%" 2>&1
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
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $rootPath=[IO.Path]::GetFullPath($env:ROOT); $root=$rootPath.TrimEnd('\'); $volumeRoot=[IO.Path]::GetPathRoot($rootPath).TrimEnd('\'); $rootWithSeparator=$root+'\'; if([string]::IsNullOrWhiteSpace($root) -or $root -ieq $volumeRoot){throw 'The project root cannot be a drive or share root.'}; foreach($target in @($env:RUNTIME,$env:VENV,$env:DOWNLOADS,$env:PYTHON_DIR,$env:SETUP_LOCK)){if([string]::IsNullOrWhiteSpace($target)){throw 'A setup target path is empty.'}; $full=[IO.Path]::GetFullPath($target).TrimEnd('\'); if(-not $full.StartsWith($rootWithSeparator,[StringComparison]::OrdinalIgnoreCase)){throw ('A setup target escaped the project folder: '+$full)}; if(Test-Path -LiteralPath $full){$item=Get-Item -LiteralPath $full -Force; if(-not $item.PSIsContainer){throw ('A setup folder path is occupied by a file: '+$full)}; if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw ('A private setup folder cannot be a link or junction: '+$full)}}}; exit 0" >>"%LOG%" 2>&1
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
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$project=[IO.Path]::GetFullPath($env:ROOT).TrimEnd('\');$root=[IO.Path]::GetFullPath($env:VALIDATE_TREE).TrimEnd('\');if(-not $root.StartsWith($project+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Private tree escaped the project root.'};$stack=New-Object 'System.Collections.Generic.Stack[string]';$stack.Push($root);while($stack.Count -gt 0){$directory=Get-Item -LiteralPath $stack.Pop() -Force;if(-not $directory.PSIsContainer-or($directory.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Unsafe private directory.'};foreach($entryPath in [IO.Directory]::EnumerateFileSystemEntries($directory.FullName)){$entry=Get-Item -LiteralPath $entryPath -Force;if($entry.Attributes-band[IO.FileAttributes]::ReparsePoint){throw 'Unsafe private reparse point.'};if($entry.PSIsContainer){$stack.Push($entry.FullName)}}};exit 0" >>"%LOG%" 2>&1
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
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $items=@(Get-ChildItem -LiteralPath $env:CHECK_DIR -Force); if($items.Count -ne 1){throw 'Install check must create exactly one result file.'}; $item=$items[0]; if($item.PSIsContainer -or $item.Name -cne 'checks.json'){throw 'Install check did not create only checks.json.'}; $data=Get-Content -LiteralPath $item.FullName -Raw | ConvertFrom-Json; if($null -eq $data){throw 'checks.json did not contain a JSON result.'}; foreach($name in @('passed','app','version','network_requests','real_desktop_captures','providers','model_entries','checks')){if($data.PSObject.Properties.Name -notcontains $name){throw ('checks.json is missing ' + $name)}}; if($data.passed -isnot [bool] -or -not $data.passed){throw 'App install check did not pass.'}; if($data.app -isnot [string] -or $data.app -cne 'AI Location Finder'){throw 'checks.json reported the wrong app.'}; if($data.version -isnot [string] -or $data.version -cne '1.0.4'){throw 'checks.json reported the wrong app version.'}; foreach($name in @('network_requests','real_desktop_captures','providers','model_entries')){if($data.$name -isnot [int] -and $data.$name -isnot [long]){throw ('checks.json has a non-integer ' + $name)}}; if($data.network_requests -ne 0 -or $data.real_desktop_captures -ne 0){throw 'App install check used network requests or desktop capture.'}; if($data.providers -ne 4){throw 'App install check reported the wrong provider count.'}; if($data.model_entries -lt 1){throw 'App install check did not report any models.'}; if($data.checks -isnot [System.Array]){throw 'App install checks must be an array.'}; $checks=@($data.checks); if($checks.Count -ne 6){throw 'App install check did not complete the expected checks.'}; foreach($check in $checks){if($check -isnot [string] -or [string]::IsNullOrWhiteSpace($check)){throw 'App install check contained an empty check.'}}; Write-Output 'Safe app install-check output verified.'" >>"%LOG%" 2>&1
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
"%POWERSHELL_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; function Get-Hash([byte[]]$bytes){$sha=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','')}finally{$sha.Dispose()}}; function Save-Checked([string]$path,[byte[]]$bytes,[string]$expected){if((Get-Hash $bytes) -ne $expected){throw ('Embedded asset hash mismatch for '+$path)};$new=$path+'.new';[IO.File]::WriteAllBytes($new,$bytes);if((Get-Hash ([IO.File]::ReadAllBytes($new))) -ne $expected){throw ('Written asset hash mismatch for '+$path)};Move-Item -LiteralPath $new -Destination $path -Force};New-Item -ItemType Directory -Path $env:ASSOCIATION_DIR -Force|Out-Null;$launcher=[Convert]::FromBase64String($env:ASSOC_LAUNCHER_B64);$restore=[Convert]::FromBase64String($env:ASSOC_RESTORE_B64);$payload=$env:ASSOC_MANAGER_GZIP_B64_1+$env:ASSOC_MANAGER_GZIP_B64_2+$env:ASSOC_MANAGER_GZIP_B64_3+$env:ASSOC_MANAGER_GZIP_B64_4;$compressed=[Convert]::FromBase64String($payload);$input=[IO.MemoryStream]::new($compressed);$gzip=[IO.Compression.GZipStream]::new($input,[IO.Compression.CompressionMode]::Decompress);$output=[IO.MemoryStream]::new();try{$gzip.CopyTo($output);$manager=$output.ToArray()}finally{$output.Dispose();$gzip.Dispose();$input.Dispose()};Save-Checked $env:ASSOCIATION_LAUNCHER $launcher $env:ASSOC_LAUNCHER_SHA256;Save-Checked $env:ASSOCIATION_MANAGER $manager $env:ASSOC_MANAGER_SHA256;Save-Checked $env:ASSOCIATION_RESTORE $restore $env:ASSOC_RESTORE_SHA256" >>"%LOG%" 2>&1
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
if exist "%ASSOCIATION_DIR%" rmdir /s /q "%ASSOCIATION_DIR%" >nul 2>nul
if not "%ASSOCIATION_TEST_CODE%"=="0" goto AssociationTestFailed
echo Shared .pyw launcher offline checks passed. No association was changed.
exit /b 0

:AssociationTestFailed
if exist "%ASSOCIATION_DIR%" rmdir /s /q "%ASSOCIATION_DIR%" >nul 2>nul
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
