@echo off
title Guardia Medica - Interfaz
cd /d "%~dp0"
call venv\Scripts\activate
python interfaz.py
