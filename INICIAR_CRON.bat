@echo off
title Guardia - Cron Envio 9hs (con reinicio automático)
echo Iniciando cron de envio automatico...
echo (El servidor WhatsApp debe estar corriendo en otra ventana)
echo.
echo Esta ventana reinicia el cron solo si el proceso se cae por algún error.
echo.
cd /d "%~dp0"
if not exist "logs" mkdir "logs"

:loop
echo [%date% %time%] Iniciando cron... >> logs\cron.log
python enviar_encuestas.py
echo.
echo [%date% %time%] El cron se detuvo (código de salida %errorlevel%). >> logs\cron.log
echo ⚠  El cron se detuvo. Reiniciando en 10 segundos...
echo    (si esto se repite todo el tiempo, revisá logs\cron.log y logs\enviar_encuestas.log)
timeout /t 10 /nobreak > nul
goto loop