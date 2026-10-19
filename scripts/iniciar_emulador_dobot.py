"""Inicia el emulador TCP/IP del Dobot CR5AS y Pinza PGE-50-26 en segundo plano.

Uso:
    python scripts/iniciar_emulador_dobot.py [--puerto 29999]

Permite ejecutar scripts de prueba del brazo físico (como `probar_jugada_brazo.py`,
`probar_conexion_dobot.py`, etc.) usando `127.0.0.1` sin requerir conexión con el robot real.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.servicios.brazo.emulador_dobot import EmuladorDobot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", type=int, default=29999, help="Puerto TCP a escuchar (por defecto 29999)")
    args = parser.parse_args()

    print(f"Iniciando Emulador Virtual Dobot CR5AS + Pinza DH PGE-50-26 en 127.0.0.1:{args.puerto}...")
    emulador = EmuladorDobot("127.0.0.1", args.puerto)
    emulador.iniciar()
    print("=" * 60)
    print(f"[OK] Emulador activo en puerto {args.puerto}.")
    print("     - Pose inicial: " + str(tuple(round(v, 2) for v in emulador.estado.pose_actual)))
    print("     - Ángulos HOME: " + str(tuple(round(v, 2) for v in emulador.estado.angulos_actuales)))
    print("     - Pinza PGE-50-26: Inicializada y lista para Modbus (puerto interno 60000).")
    print("=" * 60)
    print("Ya puedes ejecutar en otra terminal:")
    print(f"    python scripts/probar_conexion_dobot.py --host 127.0.0.1 --puerto {args.puerto}")
    print(f"    python scripts/probar_jugada_brazo.py --host 127.0.0.1 --jugada e2e4")
    print("\nPresiona Ctrl+C para detener el emulador.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nDeteniendo emulador...")
        emulador.detener()
        print("Emulador detenido con éxito.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
