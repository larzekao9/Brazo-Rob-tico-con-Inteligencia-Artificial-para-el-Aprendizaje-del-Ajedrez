@echo off
rem Turing como motor UCI para programas de ajedrez con interfaz grafica (Arena, Cute Chess, etc.).
rem Usar este archivo como "ruta del motor". Requiere Python con las dependencias del proyecto en el PATH.
cd /d "%~dp0.."
python -m training.turing_uci %*
