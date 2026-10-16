"""Comprueba, con el brazo real, que la calibración guardada deja la punta de la pinza centrada sobre las esquinas del tablero.

Usa la calibración de `calibracion_local/brazo.json` (la de `importar_puntos_dobotstudio.py` o `calibrar_brazo_tablero.py`). Para cada
esquina (a1, h1, h8, a8) el brazo va SOLO hasta un punto 80 mm por encima y, si lo confirmás, baja despacio hasta 10 mm sobre el
tablero. Cada movimiento se pide con una confirmación; la velocidad es baja (20 %). Hacelo con la mano al lado del botón de emergencia
y el espacio alrededor del brazo despejado (sin personas ni cables en el camino).

Qué mirar: de costado, que la punta quede centrada sobre la casilla y a unos 10 mm del tablero al bajar. Si alguna esquina queda corrida,
anotá hacia dónde y cuánto (en mm) y pasamelo.

Uso:
    python scripts/verificar_calibracion_brazo.py --host 192.168.5.1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from backend.servicios.brazo.calibracion_brazo import cargar_calibracion_brazo  # noqa: E402
from backend.servicios.brazo.cliente_dobot import ClienteDobot, ErrorDobot  # noqa: E402

ALTURA_DE_VERIFICACION_MM = 80.0
ALTURA_DE_CONTACTO_MM = 10.0
DIFERENCIA_MAXIMA_AL_CERO_GRADOS = 5.0


def _confirmar(pregunta: str) -> bool:
    return input(f"{pregunta} (s/n): ").strip().lower() in ("s", "si", "sí")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="192.168.5.1")
    args = parser.parse_args()

    try:
        calibracion = cargar_calibracion_brazo()
    except ValueError as error:
        raise SystemExit(str(error))
    if calibracion is None:
        raise SystemExit("Todavía no hay calibración: corré scripts/importar_puntos_dobotstudio.py o scripts/calibrar_brazo_tablero.py")

    cliente = ClienteDobot(args.host)
    try:
        cliente.conectar()
    except (OSError, ErrorDobot) as error:
        raise SystemExit(f"No se pudo conectar con el brazo: {error}")
    modo = cliente.modo()
    print(f"Conectado. Velocidad global {cliente.velocidad_global} %. Modo del brazo: {modo} (5 = habilitado y libre).")
    if modo != 5:
        cliente.cerrar()
        raise SystemExit("El brazo tiene que estar en modo 5 (habilitado y libre). Limpiá el estado en DobotStudio y repetí.")
    for aviso in calibracion.avisos:
        print(f"AVISO: {aviso}")

    try:
        diferencia = max(abs((a - b + 180) % 360 - 180) for a, b in zip(cliente.angulos(), calibracion.angulos_cero))
        if diferencia > DIFERENCIA_MAXIMA_AL_CERO_GRADOS:
            print(f"\nEl brazo no está en la posición cero (una articulación difiere {diferencia:.0f}°).")
            if not _confirmar("¿Llevarlo primero a la posición cero? (el brazo se mueve solo; despejá el espacio)"):
                raise SystemExit("Sin mover. Llevalo a mano cerca de la posición cero y repetí.")
            cliente.mover_a_angulos(calibracion.angulos_cero)
            print("En la posición cero.")

        if not _confirmar("\n¿Verificar las esquinas? (el brazo se mueve solo, a baja velocidad; mano en el botón de emergencia)"):
            return
        primera = True
        for casilla in ("a1", "h1", "h8", "a8"):
            x, y, z = calibracion.posiciones_casillas[casilla]
            if not _confirmar(f"\n¿Ir sobre {casilla} (a {ALTURA_DE_VERIFICACION_MM:.0f} mm)?"):
                print("Verificación cortada.")
                break
            cliente.mover_a_pose((x, y, z + ALTURA_DE_VERIFICACION_MM, *calibracion.orientacion), lineal=not primera)
            primera = False
            print(f"   Sobre {casilla}. Mirá desde arriba si la punta queda centrada en la casilla.")
            if _confirmar(f"   ¿Bajar despacio hasta {ALTURA_DE_CONTACTO_MM:.0f} mm sobre {casilla}?"):
                cliente.mover_a_pose((x, y, z + ALTURA_DE_CONTACTO_MM, *calibracion.orientacion), lineal=True)
                print(f"   Abajo en {casilla}. Mirá de costado: ¿centrada y a ~{ALTURA_DE_CONTACTO_MM:.0f} mm del tablero?")
                input("   Enter para volver a subir... ")
                cliente.mover_a_pose((x, y, z + ALTURA_DE_VERIFICACION_MM, *calibracion.orientacion), lineal=True)
        if _confirmar("\n¿Volver a la posición cero?"):
            cliente.mover_a_angulos(calibracion.angulos_cero)
    finally:
        cliente.cerrar()
    print("\nListo.")


if __name__ == "__main__":
    main()
