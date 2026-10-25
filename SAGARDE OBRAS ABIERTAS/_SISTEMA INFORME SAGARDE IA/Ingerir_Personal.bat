@echo off
setlocal
chcp 65001 >nul
title Sagarde - Ingerir jornadas de personal
cd /d "%~dp0"

rem Uso: arrastrar el fichero que exporta la tablet (lote_personal_....json) ENCIMA de este archivo.
rem Simula, ensena los avisos, pide confirmacion, guarda, actualiza el estado de la tablet y
rem regenera el panel de la obra. NO publica nada: para publicar, Actualizar_Sagarde.bat.

where python >nul 2>nul
if %errorlevel%==0 (set "PY=python") else (set "PY=py")

echo ============================================
echo  Personal en obra - ingerir una jornada
echo ============================================
echo.
if "%~1"=="" (
  echo Arrastra el fichero de jornada que exporta la tablet
  echo ^(lote_personal_....json^) encima de este archivo.
  echo.
  pause
  exit /b 1
)

%PY% "%~dp0personal_integracion.py" ingerir "%~1"
set "CODIGO=%errorlevel%"
echo.
if "%CODIGO%"=="0" (
  echo Terminado.
) else (
  echo Terminado SIN guardar todo o con avisos. Codigo %CODIGO%. Lee lo que pone arriba.
)
echo NO se ha publicado nada. Para publicar: Actualizar_Sagarde.bat
echo.
pause
exit /b %CODIGO%
