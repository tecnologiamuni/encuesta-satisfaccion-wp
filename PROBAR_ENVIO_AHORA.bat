@echo off
title Guardia - Prueba Envio
echo Enviando mensajes ahora (modo prueba)...
echo (El servidor WhatsApp debe estar corriendo en otra ventana)
echo.
cd /d "%~dp0"
python enviar_encuestas.py --ahora
pause
