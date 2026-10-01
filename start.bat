@echo off
echo ========================================
echo  Starting SafeGrid Platform in Docker...
echo ========================================
docker compose up --build -d
echo.
echo Waiting for SafeGrid to be ready...
timeout /t 3 /nobreak >nul
echo Opening browser at http://localhost:8080 ...
start http://localhost:8080
echo.
echo ========================================
echo  SafeGrid is running at http://localhost:8080
echo ========================================
pause
