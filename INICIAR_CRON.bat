@echo off
title Guardia - Cron Envio 9hs
echo Iniciando cron de envio automatico...
echo (El servidor WhatsApp debe estar corriendo en otra ventana)
echo.
cd /d "%~dp0"
python enviar_encuestas.py
pause
