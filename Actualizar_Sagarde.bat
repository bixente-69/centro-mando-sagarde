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

echo [0/6] Ejecutando Auditoria Pre-Vuelo de Salud de Datos...
%PY% "_SISTEMA\MOTOR\scripts\auditor_sagarde.py"
echo.

echo [1/6] Actualizando Informe Sagarde IA (Obras abiertas)...
%PY% "SAGARDE OBRAS ABIERTAS\_SISTEMA INFORME SAGARDE IA\generar_todos.py" --no-pdf
if %errorlevel% neq 0 (
  echo   [AVISO] No se pudo actualizar Obras Abiertas. El portal usara los datos existentes.
)
echo.

echo [2/6] Actualizando Post-ventas y Mantenimientos...
%PY% "POST-VENTAS\_SISTEMA\postventas_index.py"
if %errorlevel% neq 0 (
  echo   [AVISO] No se pudo actualizar Post-ventas. El portal usara los datos existentes.
)
%PY% "MANTENIMIENTOS\_SISTEMA\mantenimientos_index.py"
if %errorlevel% neq 0 (
  echo   [AVISO] No se pudo actualizar Mantenimientos. El portal usara los datos existentes.
)
echo.

echo [3/6] Generando portal principal...
%PY% "_SISTEMA\MOTOR\sagarde_portal.py"
if %errorlevel% neq 0 (
  echo.
  echo [ERROR] No se pudo generar el portal principal.
  pause
  exit /b 1
)
echo.

echo [4/6] Comprobando enlaces del portal generado...
%PY% "_SISTEMA\MOTOR\scripts\comprobar_enlaces.py"
if errorlevel 2 (
  echo   [ERROR] Faltan paginas que deberian existir. Revisa los pasos
  echo           anteriores. Se publica igual, pero conviene arreglarlo antes.
) else if errorlevel 1 (
  echo   [AVISO] Hay enlaces internos rotos en el portal generado. Quedan
  echo           listados arriba. Se publica igual, pero conviene corregirlos.
)

echo.
echo [5/6] Actualizando el mapa mental del entorno...
%PY% "_SISTEMA\MOTOR\scripts\actualizar_mapa_mental.py"
if errorlevel 2 (
  echo   [ERROR] No se pudo actualizar el mapa mental. Se publica sin tocarlo.
) else if errorlevel 1 (
  echo   [AVISO] El mapa mental declara rutas que ya no existen. Quedan escritas
  echo           dentro del propio mapa. Se publica igual, pero corrigelas: es la
  echo           lectura obligatoria al empezar sesion y manda a un sitio vacio.
)

echo.
echo [6/6] Subiendo a la nube (GitHub Pages)...
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
