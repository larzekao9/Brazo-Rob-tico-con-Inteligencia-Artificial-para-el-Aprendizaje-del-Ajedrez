"""Arranca el simulador virtual del Dobot CR5AS con la pinza DH PGE-50-26: un servidor TCP que habla el mismo protocolo que el brazo real.

    python scripts/simulador_brazo.py                       (dashboard en 127.0.0.1:29999, front en http://127.0.0.1:8765)

En otra terminal, apuntando a la calibración de ejemplo que este script escribe (no toca calibracion_local/brazo.json):

    export CALIBRACION_BRAZO_ARCHIVO=calibracion_local/simulador/brazo_ejemplo.json
    python scripts/probar_jugada_brazo.py --host 127.0.0.1 --jugada e2e4

Con el brazo real se corre lo mismo cambiando solo `--host` (y sin `CALIBRACION_BRAZO_ARCHIVO`). Ver docs/simulador_brazo.md.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import chess

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from backend.servicios.brazo.calibracion_brazo import (  # noqa: E402
    ARCHIVO_CALIBRACION_BRAZO,
    cargar_calibracion_brazo,
    cargar_parametros_agarre,
)
from backend.servicios.brazo.simulador_dobot.calibracion_ejemplo import (  # noqa: E402
    calibracion_ejemplo,
    escribir_calibracion_ejemplo,
    parametros_agarre_ejemplo,
)
from backend.servicios.brazo.simulador_dobot.nucleo import Simulador  # noqa: E402
from backend.servicios.brazo.simulador_dobot.protocolo import ProtocoloDobot  # noqa: E402
from backend.servicios.brazo.simulador_dobot.servidor_http import ServidorWeb  # noqa: E402
from backend.servicios.brazo.simulador_dobot.servidor_tcp import ServidorDashboard  # noqa: E402

RUTA_EJEMPLO = RAIZ / "calibracion_local" / "simulador" / "brazo_ejemplo.json"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--puerto-dashboard", type=int, default=29999, help="puerto TCP del dashboard (29999 es el del brazo real)")
    p.add_argument("--puerto-http", type=int, default=8765, help="puerto del front web")
    p.add_argument("--host-escucha", default="127.0.0.1", help="interfaz donde escucha (127.0.0.1 solo esta máquina; 0.0.0.0 toda la red)")
    p.add_argument("--sin-fisica", action="store_true", help="no usar PyBullet (sin choques ni vuelcos): para cuando no está instalado")
    p.add_argument("--calibracion", type=Path, default=None, help="brazo.json a leer (solo lectura); por defecto se usa la calibración de ejemplo")
    p.add_argument("--usar-calibracion-local", action="store_true", help=f"leer {ARCHIVO_CALIBRACION_BRAZO} (solo lectura) en vez del ejemplo")
    p.add_argument("--fen", default=chess.STARTING_FEN, help="posición inicial de las piezas (por defecto la inicial)")
    p.add_argument("--escala-tiempo", type=float, default=1.0, help="veces más rápido que el tiempo real (se cambia también desde el front)")
    argumentos = p.parse_args()

    ruta = argumentos.calibracion or (ARCHIVO_CALIBRACION_BRAZO if argumentos.usar_calibracion_local else None)
    if ruta is not None:
        calibracion, agarre = cargar_calibracion_brazo(ruta), cargar_parametros_agarre(ruta)
        if calibracion is None or agarre is None or agarre.z_tope is None:
            print(f"{ruta} no tiene calibración y parámetros de agarre completos (con z_tope).")
            return 1
        origen = f"calibración de {ruta}"
    else:
        calibracion, agarre = calibracion_ejemplo(), parametros_agarre_ejemplo()
        escribir_calibracion_ejemplo(RUTA_EJEMPLO)
        origen = f"calibración de EJEMPLO (escrita en {RUTA_EJEMPLO.relative_to(RAIZ)})"

    con_fisica = not argumentos.sin_fisica
    if con_fisica:
        try:
            import pybullet  # noqa: F401
        except ImportError:
            print("PyBullet no está instalado en este Python: usá el entorno conda `ajedrez` o agregá --sin-fisica.")
            return 1

    simulador = Simulador(calibracion, agarre, argumentos.fen, con_fisica, escala_tiempo=argumentos.escala_tiempo)
    try:
        dashboard = ServidorDashboard(ProtocoloDobot(simulador), argumentos.host_escucha, argumentos.puerto_dashboard)
    except OSError as error:
        print(f"No pude abrir el puerto {argumentos.puerto_dashboard} del dashboard ({error}). Probá con --puerto-dashboard 30000.")
        simulador.cerrar()
        return 1
    try:
        web = ServidorWeb(simulador, argumentos.host_escucha, argumentos.puerto_http)
    except OSError as error:
        print(f"No pude abrir el puerto {argumentos.puerto_http} del front ({error}). Probá con --puerto-http 8766.")
        dashboard.detener()
        simulador.cerrar()
        return 1

    simulador.iniciar_hilo()
    dashboard.iniciar()
    web.iniciar()
    print(f"Simulador del Dobot CR5AS + pinza DH PGE-50-26 ({'PyBullet' if con_fisica else 'sin física'}), {origen}.")
    print(f"  Dashboard TCP : {argumentos.host_escucha}:{dashboard.puerto}  (host de los scripts: 127.0.0.1)")
    print(f"  Front web     : http://{argumentos.host_escucha}:{web.puerto}")
    if ruta is None:
        print(f"  Para los scripts: export CALIBRACION_BRAZO_ARCHIVO={RUTA_EJEMPLO.relative_to(RAIZ)}")
    if dashboard.puerto != 29999:
        print("  Los scripts del proyecto usan el puerto 29999 fijo: con otro puerto hay que armar el ClienteDobot a mano.")
    print("Ctrl+C para salir.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCerrando...")
    finally:
        web.detener()
        dashboard.detener()
        simulador.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
