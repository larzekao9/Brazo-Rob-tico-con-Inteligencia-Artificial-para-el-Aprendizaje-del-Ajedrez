@echo off
REM Abre la ventana 3D de PyBullet que refleja en vivo la partida activa en la web.
REM Uso: ver_simulacion_3d.bat <partida_id> <token>   (o sin argumentos, el script te va a explicar como conseguirlos)
REM El token se consigue haciendo login en la app y copiando el access_token.
cd /d "%~dp0"
"C:\Users\USUARIO\miniconda3\envs\ajedrez\python.exe" -m backend.servicios.simulacion.ver_partida_en_vivo %*
pause
