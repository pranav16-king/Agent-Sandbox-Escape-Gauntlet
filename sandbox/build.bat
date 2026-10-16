@echo off
rem ==============================================================================
rem PS01 Agent Sandbox Escape Gauntlet - Hardened Sandbox Image Builder
rem Targets: ps01-sandbox:latest
rem ==============================================================================
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%..\"
set "IMAGE_NAME=ps01-sandbox:latest"

echo ================================================================================
echo [PS01] Building Hardened Agent Sandbox Container Image
echo ================================================================================
echo   Target Tag:  %IMAGE_NAME%
echo   Dockerfile:  %SCRIPT_DIR%Dockerfile
echo   Context:     %ROOT_DIR%
echo --------------------------------------------------------------------------------

where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [PS01] ERROR: 'docker' command could not be found.
    echo        Please ensure Docker Desktop / Docker Engine is installed and in your PATH.
    exit /b 1
)

docker build -t "%IMAGE_NAME%" -f "%SCRIPT_DIR%Dockerfile" "%ROOT_DIR%" %*

if %ERRORLEVEL% NEQ 0 (
    echo [PS01] ERROR: Docker build failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo --------------------------------------------------------------------------------
echo [PS01] Successfully built image: %IMAGE_NAME%
echo ================================================================================
exit /b 0
