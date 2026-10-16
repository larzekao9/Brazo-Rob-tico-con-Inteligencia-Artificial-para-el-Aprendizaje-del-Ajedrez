"""Enseña al brazo dónde está el tablero: posición cero y 3 casillas (a1, h1 y a8), llevando el brazo A MANO.

El programa NO mueve el brazo por su cuenta mientras enseñás: vos lo llevás con el modo arrastre (el botón de arrastre del propio
brazo o el de DobotStudio Pro) y el programa solo LEE su posición con `GetPose()` y `GetAngle()` cuando le decís. Recién en el
último paso, y solo si lo confirmás, el brazo se mueve solo hasta un punto sobre cada esquina para que verifiques a ojo.

Antes de empezar:
  - Brazo encendido, habilitado y en modo TCP (DobotStudio Pro lo muestra como "Device mode: TCP"). Mano al lado del botón de emergencia.
  - El tablero y la cámara ya en su lugar definitivo: si se mueven, hay que volver a enseñar.
  - Pinza montada (o la herramienta que vayas a usar). La pinza tiene que apuntar hacia el tablero, igual en los 3 puntos.

Qué enseñás:
  1. POSICIÓN CERO: la pose de descanso del brazo, fuera del encuadre de la cámara, desde donde empieza y termina cada jugada.
  2. a1, h1 y a8: llevá la punta de la pinza al centro de cada casilla, casi tocando el tablero (1 a 2 mm de aire; sin apoyar).

Uso:
    python scripts/calibrar_brazo_tablero.py --host 192.168.5.1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from backend.servicios.brazo.calibracion_brazo import (  # noqa: E402
    ARCHIVO_CALIBRACION_BRAZO,
    CASILLAS_ENSENADAS,
    guardar_calibracion_brazo,
)
from backend.servicios.brazo.cliente_dobot import ClienteDobot, ErrorDobot  # noqa: E402

ALTURA_DE_VERIFICACION_MM = 80.0
ALTURA_DE_CONTACTO_MM = 10.0


def _confirmar(pregunta: str) -> bool:
    return input(f"{pregunta} (s/n): ").strip().lower() in ("s", "si", "sí")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="192.168.5.1")
    args = parser.parse_args()

    cliente = ClienteDobot(args.host)
    try:
        cliente.conectar()
    except (OSError, ErrorDobot) as error:
        raise SystemExit(f"No se pudo conectar con el brazo: {error}")
    print(f"Conectado. Velocidad global {cliente.velocidad_global} %. Modo del brazo: {cliente.modo()} (5 = habilitado y libre).")

    try:
        input("\n1) POSICIÓN CERO. Llevá el brazo a mano a su pose de descanso y apretá Enter para guardarla... ")
        angulos_cero = cliente.angulos()
        print(f"   Posición cero guardada: {tuple(round(a, 1) for a in angulos_cero)}")

        puntos: dict[str, tuple[float, ...]] = {}

        def ensenar(casilla: str) -> None:
            if casilla == "a1":
                consigna = ("apoyá la punta de la pinza sobre una tarjeta puesta en el CENTRO de a1, rozándola sin apretar: de esta casilla "
                            "sale la ALTURA del tablero")
            else:
                consigna = (f"llevá la punta al CENTRO de {casilla}. Acá solo importa la posición X e Y: podés dejar la pinza 2 o 3 cm "
                            "más arriba para ver mejor el centro, pero apuntando igual que en a1")
            input(f"\n2) CASILLA {casilla}: {consigna}. Enter... ")
            puntos[casilla] = cliente.pose()
            print(f"   {casilla}: x={puntos[casilla][0]:.1f} y={puntos[casilla][1]:.1f} z={puntos[casilla][2]:.1f} "
                  f"rx={puntos[casilla][3]:.1f} ry={puntos[casilla][4]:.1f} rz={puntos[casilla][5]:.1f}")

        for casilla in CASILLAS_ENSENADAS:
            ensenar(casilla)

        while True:
            try:
                calibracion = guardar_calibracion_brazo(angulos_cero, puntos)
                break
            except ValueError as error:
                print(f"\nNo se guardó: {error}")
                otra = input("¿Qué casilla querés volver a enseñar? (a1/h1/a8, o Enter para salir sin guardar): ").strip().lower()
                if otra not in CASILLAS_ENSENADAS:
                    raise SystemExit("Salida sin guardar.")
                ensenar(otra)
        print(f"\nGuardado en {ARCHIVO_CALIBRACION_BRAZO}")
        for aviso in calibracion.avisos:
            print(f"AVISO: {aviso}")
        print(f"Orientación de la herramienta: {tuple(round(v, 1) for v in calibracion.orientacion)}")

        if _confirmar(f"\n3) VERIFICAR: ¿mover el brazo solo hasta {ALTURA_DE_VERIFICACION_MM:.0f} mm SOBRE cada esquina (a1, h1, h8, a8)? "
                      "Tené la mano en el botón de emergencia y el espacio libre"):
            for casilla in ("a1", "h1", "h8", "a8"):
                x, y, z = calibracion.posiciones_casillas[casilla]
                destino = (x, y, z + ALTURA_DE_VERIFICACION_MM, *calibracion.orientacion)
                if not _confirmar(f"   ¿Ir sobre {casilla}?"):
                    print("   Verificación cortada.")
                    break
                cliente.mover_a_pose(destino, lineal=casilla != "a1")
                print(f"   Sobre {casilla}. Revisá que la punta quede centrada sobre la casilla (a {ALTURA_DE_VERIFICACION_MM:.0f} mm).")
            if _confirmar(f"   ¿Bajar despacio a {ALTURA_DE_CONTACTO_MM:.0f} mm sobre a1 para comprobar la altura del tablero? (la punta debe quedar "
                          "a casi nada de la superficie, sin tocarla)"):
                x, y, z = calibracion.posiciones_casillas["a1"]
                cliente.mover_a_pose((x, y, z + ALTURA_DE_CONTACTO_MM, *calibracion.orientacion), lineal=True)
                print("   Mirá la distancia entre la punta y el tablero: tendría que ser de ~10 mm.")
            if _confirmar("   ¿Volver a la posición cero?"):
                cliente.mover_a_angulos(calibracion.angulos_cero)
    finally:
        cliente.cerrar()
    print("\nListo.")


if __name__ == "__main__":
    main()
