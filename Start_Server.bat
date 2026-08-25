@echo off
setlocal EnableExtensions

REM ==========================================================
REM HTML Converter Studio - LOCAL Launcher v3
REM Fixes: "No module named uvicorn" caused by wrong Python interpreter.
REM This version uses venv\Scripts\python.exe directly instead of relying on activation.
REM Place this BAT file in the main project folder.
REM ==========================================================

set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"
set "VENV_PY=%BACKEND_DIR%\venv\Scripts\python.exe"
set "BACKEND_URL=http://127.0.0.1:8000"
set "FRONTEND_URL=http://127.0.0.1:5173"

cls
echo.
echo ==========================================================
echo   HTML Converter Studio - LOCAL Launcher v3
echo ==========================================================
echo Project : %PROJECT_DIR%
echo Python  : %VENV_PY%
echo Backend : %BACKEND_URL%
echo Frontend: %FRONTEND_URL%
echo ==========================================================
echo.

REM -------------------------------
REM Basic folder/file checks
REM -------------------------------
if not exist "%VENV_PY%" (
    echo [ERROR] venv Python not found:
    echo %VENV_PY%
    echo.
    echo Please confirm venv exists under the project folder.
    pause
    exit /b 1
)

if not exist "%BACKEND_DIR%\app.py" (
    echo [ERROR] app.py not found in backend folder.
    pause
    exit /b 1
)

if not exist "%BACKEND_DIR%\converter_pdf.py" (
    echo [ERROR] converter_pdf.py not found in backend folder.
    pause
    exit /b 1
)

if not exist "%BACKEND_DIR%\converter_pptx.py" (
    echo [ERROR] converter_pptx.py not found in backend folder.
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERROR] frontend\package.json not found:
    echo %FRONTEND_DIR%\package.json
    pause
    exit /b 1
)

REM -------------------------------
REM Check backend Python packages
REM -------------------------------
echo Checking backend Python packages in venv...
"%VENV_PY%" -c "import uvicorn, fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INFO] uvicorn/FastAPI not found in venv. Installing required backend packages...
    "%VENV_PY%" -m pip install uvicorn fastapi python-multipart >nul
    if errorlevel 1 (
        echo [ERROR] Failed to install backend packages. Check internet/proxy/pip access.
        pause
        exit /b 1
    )
)

REM -------------------------------
REM Stop old processes using ports 8000 and 5173
REM -------------------------------
echo Checking old processes on ports 8000 and 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Stopping existing process on port 8000: %%a
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo Stopping existing process on port 5173: %%a
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

REM -------------------------------
REM Start backend in separate window
REM Uses venv python directly to avoid wrong global Python.
REM -------------------------------
echo Starting backend...
start "HTML Converter Studio - Backend" /D "%BACKEND_DIR%" cmd /k ""%VENV_PY%" -m py_compile converter_pdf.py && "%VENV_PY%" -m py_compile converter_pptx.py && "%VENV_PY%" -m py_compile app.py && "%VENV_PY%" -m uvicorn app:app --host 127.0.0.1 --port 8000"

REM -------------------------------
REM Wait until backend /health responds
REM -------------------------------
echo Waiting for backend to become ready...
set "BACKEND_READY=0"
for /L %%i in (1,1,30) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing '%BACKEND_URL%/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "BACKEND_READY=1"
        goto backend_ready
    )
    timeout /t 1 /nobreak >nul
)

:backend_ready
if "%BACKEND_READY%"=="0" (
    echo.
    echo [WARNING] Backend did not respond at %BACKEND_URL%/health within 30 seconds.
    echo Please check the Backend window for errors.
    echo.
) else (
    echo Backend is ready.
)

REM -------------------------------
REM Start frontend in separate window
REM -------------------------------
echo Starting frontend...
start "HTML Converter Studio - Frontend" /D "%FRONTEND_DIR%" cmd /k "npm run dev -- --host 127.0.0.1 --port 5173"

REM -------------------------------
REM Wait until frontend responds
REM -------------------------------
echo Waiting for frontend to become ready...
set "FRONTEND_READY=0"
for /L %%i in (1,1,30) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing '%FRONTEND_URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "FRONTEND_READY=1"
        goto frontend_ready
    )
    timeout /t 1 /nobreak >nul
)

:frontend_ready
if "%FRONTEND_READY%"=="0" (
    echo.
    echo [WARNING] Frontend did not respond at %FRONTEND_URL% within 30 seconds.
    echo Please check the Frontend window for errors.
    echo.
) else (
    echo Frontend is ready.
)

REM -------------------------------
REM Open UI
REM -------------------------------
echo Opening UI...
start "" "%FRONTEND_URL%"

echo.
echo ==========================================================
echo Launcher completed.
echo Keep both Backend and Frontend command windows open.
echo UI: %FRONTEND_URL%
echo Backend docs: %BACKEND_URL%/docs
echo ==========================================================
echo.

endlocal
exit /b 0
