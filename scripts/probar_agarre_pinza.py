"""Prueba la pinza SOLA, sin mover el brazo: abre, vos ponés una pieza a mano entre los dedos y cierra imprimiendo posición y estado.

    python scripts/probar_agarre_pinza.py --host 192.168.5.1

Sirve para separar un problema de la pinza (fuerza, detección) de uno de posición del brazo. Si con la pieza puesta a mano el agarre da 2,
la pinza funciona y lo que falla es dónde baja el brazo.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.servicios.brazo.calibracion_brazo import cargar_parametros_agarre  # noqa: E402
from backend.servicios.brazo.cliente_dobot import ClienteDobot  # noqa: E402
from backend.servicios.brazo.pinza_dh import REG_POSICION, PinzaDH  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="192.168.5.1", help="IP del controlador del Dobot")
    p.add_argument("--apertura", type=int, default=None, help="apertura inicial, 0 a 1000 (por defecto la de aproximación guardada)")
    p.add_argument("--fuerza", type=int, default=None, help="fuerza de la pinza, 20 a 100 (por defecto la guardada)")
    argumentos = p.parse_args()

    parametros = cargar_parametros_agarre()
    apertura = argumentos.apertura if argumentos.apertura is not None else (parametros.apertura_aproximacion if parametros else 560)
    fuerza = argumentos.fuerza if argumentos.fuerza is not None else (parametros.fuerza if parametros else 20)

    cliente = ClienteDobot(argumentos.host)
    cliente.conectar()
    pinza = PinzaDH(cliente, fuerza=fuerza, velocidad=parametros.velocidad_pinza if parametros else 20)
    try:
        pinza.conectar()
        if not pinza.estado().inicializada:
            pinza.inicializar()
        pinza.mover_a(apertura)
        print(f"Pinza abierta en {apertura}, fuerza {fuerza} %.")
        input("Poné la pieza a mano entre los dedos, sin tocarlos, y dale Enter para cerrar... ")
        pinza.escribir(REG_POSICION, 0)
        inicio = time.monotonic()
        while time.monotonic() - inicio < 4.0:
            estado = pinza.estado()
            print(f"  {time.monotonic() - inicio:4.1f} s  agarre={estado.agarre}  posición={estado.posicion}")
            time.sleep(0.2)
        input("Sostené la pieza con la mano por si cae. Enter para abrir... ")
        pinza.mover_a(apertura)
    finally:
        pinza.desconectar()
        cliente.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
