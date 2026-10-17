"""Mueve UNA pieza con el brazo real (sin captura) para probar el agarre: levanta la pieza de la casilla de origen y la deja en la de destino.

    python scripts/probar_jugada_brazo.py --host 192.168.5.1 --jugada e2e4

Antes de correrlo: brazo encendido, habilitado y en modo TCP; la pieza puesta en la casilla de origen; la mano en el botón de parada de
emergencia. Usa la calibración y los parámetros de agarre guardados en calibracion_local/brazo.json. Va al 20 % de velocidad.
Con `--ensayo` solo muestra las poses por las que pasaría, sin conectarse al brazo.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.servicios.brazo.calibracion_brazo import cargar_calibracion_brazo, cargar_parametros_agarre  # noqa: E402
from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal  # noqa: E402
from backend.servicios.brazo.pinza_dh import REG_POSICION  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="192.168.5.1", help="IP del controlador del Dobot")
    p.add_argument("--jugada", default="e2e4", help="jugada en UCI, sin captura (por defecto e2e4)")
    p.add_argument("--fen", default=chess.STARTING_FEN,
                   help="posición desde la que se juega (por defecto la inicial): sirve para jugar con piezas que ahí están bloqueadas")
    p.add_argument("--velocidad", type=int, default=20, help="SpeedFactor del brazo, 1 a 100")
    p.add_argument("--ensayo", action="store_true", help="solo mostrar las poses, sin mover nada")
    p.add_argument("--solo-bajar", action="store_true",
                   help="baja sobre la casilla de origen con la pinza abierta y espera, sin cerrarla: para ver el centrado")
    p.add_argument("--solo-cerrar", action="store_true",
                   help="baja, cierra la pinza imprimiendo posición y estado cada 0,1 s, y espera: para ver qué siente al apretar")
    p.add_argument("--fuerza", type=int, default=None, help="fuerza de la pinza, 20 a 100 (por defecto la guardada, 20)")
    p.add_argument("--margen-agarre", type=float, default=None,
                   help="mm sobre el tablero a los que agarra (por defecto el guardado, 3): subirlo toma la pieza más arriba de la base")
    argumentos = p.parse_args()

    calibracion, parametros = cargar_calibracion_brazo(), cargar_parametros_agarre()
    if calibracion is None or parametros is None:
        print("Falta la calibración o los parámetros de agarre (calibracion_local/brazo.json).")
        return 1
    if argumentos.margen_agarre is not None:
        parametros = dataclasses.replace(parametros, margen_agarre_mm=argumentos.margen_agarre)
    if argumentos.fuerza is not None:
        parametros = dataclasses.replace(parametros, fuerza=argumentos.fuerza)
    tablero = chess.Board(argumentos.fen)
    jugada = chess.Move.from_uci(argumentos.jugada)
    if jugada not in tablero.legal_moves or tablero.is_capture(jugada):
        print(f"{argumentos.jugada} no es una jugada legal sin captura desde esa posición.")
        return 1

    ejecutor = EjecutorReal(
        host=argumentos.host,
        posiciones_casillas=calibracion.posiciones_casillas,
        orientacion=calibracion.orientacion,
        angulos_cero=calibracion.angulos_cero,
        velocidad_global=argumentos.velocidad,
        parametros=parametros,
    )
    origen, destino = chess.square_name(jugada.from_square), chess.square_name(jugada.to_square)
    pieza = tablero.piece_at(jugada.from_square).symbol().lower()
    print(f"{origen} -> {destino}: agarra a z={parametros.z_agarre:.2f}, altura segura +{parametros.altura_segura_mm:.0f} mm, "
          f"giro {parametros.giro_diagonal_grados:.0f}°, pieza '{pieza}', apertura {parametros.apertura_para(pieza)}")
    for nombre, casilla in (("origen", origen), ("destino", destino)):
        print(f"  {nombre} {casilla}: pose de agarre {tuple(round(v, 2) for v in ejecutor._pose(casilla))}")
    if argumentos.ensayo:
        return 0

    input("Mano en la parada de emergencia y la pieza en el origen. Enter para mover (Ctrl+C cancela)... ")
    ejecutor.conectar()
    try:
        if argumentos.solo_cerrar:
            ejecutor.bajar_a(origen, pieza)
            print("Cerrando: segundos, estado de agarre (0 moviendo, 1 llegó, 2 sostiene, 3 se cayó), posición")
            ejecutor.pinza.escribir(REG_POSICION, 0)
            inicio = time.monotonic()
            while time.monotonic() - inicio < 5.0:
                estado = ejecutor.pinza.estado()
                print(f"  {time.monotonic() - inicio:4.1f} s  agarre={estado.agarre}  posición={estado.posicion}")
                time.sleep(0.1)
            input("Mirá si la pieza quedó apretada o se escapó. Enter para abrir y subir... ")
            ejecutor.subir_de(origen, pieza)
            ejecutor.cliente.mover_a_angulos(calibracion.angulos_cero)
        elif argumentos.solo_bajar:
            ejecutor.bajar_a(origen, pieza)
            print("Pose real abajo (x, y, z, rx, ry, rz):", tuple(round(v, 2) for v in ejecutor.cliente.pose()))
            input("Mirá cómo quedan los dedos alrededor de la pieza. Enter para subir... ")
            ejecutor.subir_de(origen, pieza)
            ejecutor.cliente.mover_a_angulos(calibracion.angulos_cero)
        else:
            ejecutor.ejecutar_movimiento(tablero, jugada)
        print("Listo.")
    finally:
        ejecutor.desconectar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
