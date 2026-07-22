@echo off
setlocal
chcp 65001 >nul
title Sagarde - Actualizando centro de mando
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (set "PY=python") else (set "PY=py")

echo ============================================
echo  Centro de mando Sagarde - actualizacion completa
echo ============================================
echo.

echo [1/4] Actualizando Informe Sagarde IA (Obras abiertas)...
%PY% "SAGARDE OBRAS ABIERTAS\_SISTEMA INFORME SAGARDE IA\generar_todos.py" --no-pdf
if %errorlevel% neq 0 (
  echo   [AVISO] No se pudo actualizar Obras Abiertas. El portal usara los datos existentes.
)
echo.

echo [2/4] Actualizando Post-ventas...
%PY% "POST-VENTAS\postventas_index.py"
if %errorlevel% neq 0 (
  echo   [AVISO] No se pudo actualizar Post-ventas. El portal usara los datos existentes.
)
echo.

echo [3/4] Generando portal principal...
%PY% "_MOTOR_SAGARDE\sagarde_portal.py"
if %errorlevel% neq 0 (
  echo.
  echo [ERROR] No se pudo generar el portal principal.
  pause
  exit /b 1
)

echo.
echo [4/4] Subiendo a la nube (GitHub Pages)...
set "GITCMD="
where git >nul 2>nul
if %errorlevel%==0 set "GITCMD=git"

if not defined GITCMD if exist "%ProgramFiles%\Git\cmd\git.exe" set "GITCMD=%ProgramFiles%\Git\cmd\git.exe"
if not defined GITCMD if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GITCMD=%ProgramFiles(x86)%\Git\cmd\git.exe"

if not defined GITCMD (
  for /d %%d in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do (
    if exist "%%~fd\resources\app\git\cmd\git.exe" set "GITCMD=%%~fd\resources\app\git\cmd\git.exe"
  )
)

for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "FECHA=%%d"

if defined GITCMD (
  echo   Usando Git: %GITCMD%
  "%GITCMD%" add -A
  "%GITCMD%" diff --cached --quiet
  if errorlevel 1 (
    "%GITCMD%" commit -m "Actualizacion %FECHA%"
    if errorlevel 1 (
      echo   [ERROR] No se pudo crear el commit. No se intentara subir.
      pause
      exit /b 1
    )
    "%GITCMD%" push origin main
    if errorlevel 1 (
      echo   [ERROR] No se pudo subir a GitHub. Los cambios siguen guardados localmente.
      pause
      exit /b 1
    ) else (
      echo   Portal actualizado en https://bixente-69.github.io/centro-mando-sagarde/
    )
  ) else (
    echo   No hay cambios nuevos que subir.
  )
) else (
  echo   [ERROR] Git no encontrado ni en PATH, ni en Git para Windows, ni en GitHub Desktop.
  echo   Instala GitHub Desktop o Git para Windows y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)

echo.
echo Centro de mando actualizado.
echo (Para regenerar tambien los PDF moviles de cada obra, ejecuta el
echo  Actualizar_Obras.bat dentro de "SAGARDE OBRAS ABIERTAS\_SISTEMA INFORME SAGARDE IA".)
if /I not "%~1"=="--no-open" start "" "index.html"
timeout /t 2 >nul
endlocal
exit /b 0
