@echo off
title Servidor WhatsApp (con reinicio automático)
echo ============================================
echo   GUARDIA MEDICA - Servidor WhatsApp Web.js
echo ============================================
echo.
echo Iniciando servidor...
echo La primera vez vas a ver un QR para escanear con el celular.
echo.
echo Esta ventana reinicia el servidor solo si se cae por algún error.
echo Dejala abierta siempre que quieras enviar mensajes.
echo.
cd /d "%~dp0whatsapp-server"
if not exist "..\logs" mkdir "..\logs"

:loop
echo [%date% %time%] Iniciando servidor WhatsApp... >> ..\logs\whatsapp-server.log
node server.js
echo.
echo [%date% %time%] El servidor se detuvo (código de salida %errorlevel%). >> ..\logs\whatsapp-server.log
echo ⚠  El servidor se detuvo. Reiniciando en 10 segundos...
echo    (si esto se repite todo el tiempo, revisá logs\whatsapp-server.log)
timeout /t 10 /nobreak > nul
goto loop