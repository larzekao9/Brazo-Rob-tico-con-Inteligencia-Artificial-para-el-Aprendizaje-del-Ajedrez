"""Arranca el simulador virtual del Dobot CR5AS con la pinza DH PGE-50-26: un servidor TCP que habla el mismo protocolo que el brazo real.

    python scripts/simulador_brazo.py                       (dashboard en 127.0.0.1:29999, front en http://127.0.0.1:8765)

Más fácil: ./scripts/simulador_brazo.sh (usa el Python del entorno conda `ajedrez`, que trae PyBullet y python-chess).

En otra terminal, apuntando a la calibración de ejemplo que este script escribe (no toca calibracion_local/brazo.json):

    export CALIBRACION_BRAZO_ARCHIVO=calibracion_local/simulador/brazo_ejemplo.json
    python scripts/probar_jugada_brazo.py --host 127.0.0.1 --jugada e2e4

Con el brazo real se corre lo mismo cambiando solo `--host` (y sin `CALIBRACION_BRAZO_ARCHIVO`). Ver docs/simulador_brazo.md.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def _pythons_del_entorno() -> list[Path]:
    """Dónde suele estar el Python del entorno conda `ajedrez`, para sugerirlo cuando falta un módulo."""
    bases = [Path(os.environ[v]).parent.parent for v in ("CONDA_EXE", "_CONDA_EXE") if os.environ.get(v)]
    bases += [Path("/opt/homebrew/Caskroom/miniforge/base"), *(Path.home() / n for n in ("miniforge3", "miniconda3", "anaconda3", "mambaforge"))]
    return [b / "envs" / "ajedrez" / "bin" / "python" for b in bases if (b / "envs" / "ajedrez" / "bin" / "python").exists()]


def _explicar_modulo_faltante(error: ModuleNotFoundError) -> int:
    sugeridos = _pythons_del_entorno()
    print(f"Este Python ({sys.executable}) no tiene el módulo '{error.name}'.")
    print("El simulador necesita el entorno conda `ajedrez` (trae python-chess y PyBullet). Opciones:")
    print("  - ./scripts/simulador_brazo.sh")
    print("  - conda activate ajedrez && python scripts/simulador_brazo.py")
    if sugeridos:
        print(f"  - {sugeridos[0]} scripts/simulador_brazo.py")
    print("Sin PyBullet se puede probar igual con --sin-fisica (python-chess sigue haciendo falta).")
    return 1


try:
    import chess

    from backend.servicios.brazo.calibracion_brazo import (
        ARCHIVO_CALIBRACION_BRAZO,
        cargar_calibracion_brazo,
        cargar_parametros_agarre,
    )
    from backend.servicios.brazo.simulador_dobot.calibracion_ejemplo import (
        calibracion_ejemplo,
        escribir_calibracion_ejemplo,
        parametros_agarre_ejemplo,
    )
    from backend.servicios.brazo.simulador_dobot.nucleo import Simulador
    from backend.servicios.brazo.simulador_dobot.protocolo import ProtocoloDobot
    from backend.servicios.brazo.simulador_dobot.servidor_http import ServidorWeb
    from backend.servicios.brazo.simulador_dobot.servidor_tcp import ServidorDashboard
except ModuleNotFoundError as error:
    if __name__ == "__main__":
        sys.exit(_explicar_modulo_faltante(error))
    raise

RUTA_EJEMPLO = RAIZ / "calibracion_local" / "simulador" / "brazo_ejemplo.json"
RUTA_AGARRE_PROPIO = RAIZ / "calibracion_local" / "simulador" / "agarre_simulador.json"


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
    p.add_argument("--restablecer-ejemplo", action="store_true", help="vuelve a escribir la calibración de ejemplo y descarta los parámetros guardados desde el front")
    argumentos = p.parse_args()

    ruta = argumentos.calibracion or (ARCHIVO_CALIBRACION_BRAZO if argumentos.usar_calibracion_local else None)
    if ruta is not None:
        calibracion, agarre = cargar_calibracion_brazo(ruta), cargar_parametros_agarre(ruta)
        if calibracion is None or agarre is None or agarre.z_tope is None:
            print(f"{ruta} no tiene calibración y parámetros de agarre completos (con z_tope).")
            return 1
        origen = f"calibración de {ruta}"
        persistencia = RUTA_AGARRE_PROPIO
        guardado = cargar_parametros_agarre(persistencia)
        if guardado is not None and guardado.z_tope is not None:
            agarre = guardado
            origen += f" (parámetros de agarre de {persistencia.relative_to(RAIZ)})"
    else:
        calibracion, agarre = calibracion_ejemplo(), parametros_agarre_ejemplo()
        persistencia = RUTA_EJEMPLO
        guardado = None if argumentos.restablecer_ejemplo else cargar_parametros_agarre(persistencia)
        if guardado is not None and guardado.z_tope is not None:
            agarre = guardado
            origen = f"calibración de EJEMPLO con los parámetros guardados en {RUTA_EJEMPLO.relative_to(RAIZ)}"
        else:
            escribir_calibracion_ejemplo(RUTA_EJEMPLO)
            origen = f"calibración de EJEMPLO (escrita en {RUTA_EJEMPLO.relative_to(RAIZ)})"

    con_fisica = not argumentos.sin_fisica
    if con_fisica:
        try:
            import pybullet  # noqa: F401
        except ImportError:
            return _explicar_modulo_faltante(ModuleNotFoundError("PyBullet no está instalado", name="pybullet"))

    simulador = Simulador(calibracion, agarre, argumentos.fen, con_fisica, escala_tiempo=argumentos.escala_tiempo, ruta_persistencia=persistencia)
    try:
        dashboard = ServidorDashboard(ProtocoloDobot(simulador), argumentos.host_escucha, argumentos.puerto_dashboard)
    except OSError as error:
        print(f"No pude abrir el puerto {argumentos.puerto_dashboard} del dashboard ({error}). Probá con --puerto-dashboard 30000.")
        simulador.cerrar()
        return 1
    try:
        web = ServidorWeb(simulador, argumentos.host_escucha, argumentos.puerto_http, puerto_dashboard=dashboard.puerto)
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
    print(f"  Front web     : http://{argumentos.host_escucha}:{web.puerto}  (página de respaldo; la API para el front React está en /api/*)")
    print(f"  Parámetros    : se guardan en {persistencia.relative_to(RAIZ)} (nunca en calibracion_local/brazo.json)")
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
