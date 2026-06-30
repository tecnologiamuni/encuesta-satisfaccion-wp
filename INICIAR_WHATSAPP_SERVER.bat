@echo off
title Servidor WhatsApp
echo ============================================
echo   GUARDIA MEDICA - Servidor WhatsApp Web.js
echo ============================================
echo.
echo Iniciando servidor...
echo La primera vez vas a ver un QR para escanear con el celular.
echo Dejá esta ventana abierta siempre que quieras enviar mensajes.
echo.
cd /d "%~dp0whatsapp-server"
node server.js
pause
