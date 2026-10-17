"""Encuentra a mano la apertura de bajada de la pinza para un tipo de pieza, sin regla.

    python scripts/ajustar_apertura_pieza.py --host 192.168.5.1 --pieza n --inicial 700

El brazo baja con la pinza abierta a una casilla VACÍA y lejos de las demás piezas (por defecto c5). Vos metés la pieza a mano, desde el
costado, entre los dedos (ahí queda la pieza entera, cabeza incluida): si no pasa o roza, abrís más; si pasa con luz de sobra, cerrás un
poco. Cuando pasa justa y con algo de luz, guardás: queda en calibracion_local/brazo.json, en `aperturas_por_pieza`, con una holgura extra.

Comandos: `+` / `-` abren / cierran 40 (unos 1 mm entre dedos), `++` / `--` 100, un número (0 a 1000) va directo a esa posición,
`g` guarda la apertura actual más la holgura, `s` sale sin guardar. Al salir el brazo sube y vuelve a la posición cero.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.servicios.brazo.calibracion_brazo import (  # noqa: E402
    cargar_calibracion_brazo,
    cargar_parametros_agarre,
    guardar_parametros_agarre,
)
from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal  # noqa: E402
from backend.servicios.brazo.pinza_dh import ancho_mm_para_posicion  # noqa: E402

PASOS = {"+": 40, "-": -40, "++": 100, "--": -100}
PIEZAS = {"p": "peón", "n": "caballo", "b": "alfil", "r": "torre", "q": "dama", "k": "rey"}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="192.168.5.1", help="IP del controlador del Dobot")
    p.add_argument("--pieza", required=True, choices=sorted(PIEZAS), help="tipo de pieza: p, n, b, r, q o k")
    p.add_argument("--inicial", type=int, default=700, help="apertura con la que empieza, 0 a 1000 (por defecto 700)")
    p.add_argument("--casilla", default="c5", help="casilla vacía sobre la que baja (por defecto c5)")
    p.add_argument("--holgura", type=int, default=40, help="se suma a la apertura al guardar (por defecto 40, unos 1 mm)")
    p.add_argument("--velocidad", type=int, default=20, help="SpeedFactor del brazo, 1 a 100")
    argumentos = p.parse_args()

    calibracion, parametros = cargar_calibracion_brazo(), cargar_parametros_agarre()
    if calibracion is None or parametros is None:
        print("Falta la calibración o los parámetros de agarre (calibracion_local/brazo.json).")
        return 1
    if not 0 <= argumentos.inicial <= 1000:
        print("La apertura inicial tiene que estar entre 0 y 1000.")
        return 1

    pieza, apertura = argumentos.pieza, argumentos.inicial
    de_prueba = dataclasses.replace(parametros, aperturas_por_pieza={**parametros.aperturas_por_pieza, pieza: apertura})
    ejecutor = EjecutorReal(
        host=argumentos.host,
        posiciones_casillas=calibracion.posiciones_casillas,
        orientacion=calibracion.orientacion,
        angulos_cero=calibracion.angulos_cero,
        velocidad_global=argumentos.velocidad,
        parametros=de_prueba,
    )
    print(f"Voy a bajar sobre {argumentos.casilla} (tiene que estar VACÍA y sin piezas cerca) con apertura {apertura} para el {PIEZAS[pieza]}.")
    input("Mano en la parada de emergencia. Enter para mover (Ctrl+C cancela)... ")
    ejecutor.conectar()
    try:
        ejecutor.cliente.mover_a_angulos(calibracion.angulos_cero)
        ejecutor.bajar_a(argumentos.casilla, pieza)
        print("Abajo. Metele el " + PIEZAS[pieza] + " a mano entre los dedos, desde el costado.")
        while True:
            orden = input(f"[{apertura} ≈ {ancho_mm_para_posicion(apertura):.1f} mm] + - ++ -- número, g guardar, s salir: ").strip().lower()
            if orden == "s":
                print("Salgo sin guardar.")
                break
            if orden == "g":
                final = min(1000, apertura + argumentos.holgura)
                nuevas = {**parametros.aperturas_por_pieza, pieza: final}
                guardar_parametros_agarre(dataclasses.replace(parametros, aperturas_por_pieza=nuevas))
                print(f"Guardado: {PIEZAS[pieza]} = {final}.")
                break
            if orden in PASOS:
                nueva = apertura + PASOS[orden]
            elif orden.isdigit():
                nueva = int(orden)
            else:
                print("No entendí la orden.")
                continue
            if not 0 <= nueva <= 1000:
                print("Fuera de rango (0 a 1000).")
                continue
            apertura = nueva
            ejecutor.pinza.mover_a(apertura)
        input("Sacá la pieza. Enter para que el brazo suba y vuelva a la posición cero... ")
        ejecutor.parametros.aperturas_por_pieza[pieza] = apertura  # sube con la apertura que quedó, no con la inicial
        ejecutor.pinza.mover_a(apertura)
        ejecutor.subir_de(argumentos.casilla, pieza)
        ejecutor.cliente.mover_a_angulos(calibracion.angulos_cero)
    finally:
        ejecutor.desconectar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
