"""Marca, una sola vez, las 4 esquinas del tablero en la foto de la cámara fija.

Abre una ventana con la foto de la cámara (la de `CAMARA_FUENTE`). Hacé clic, en este orden, en la esquina EXTERIOR del ÁREA DE
JUEGO (las casillas 8x8, no el borde de madera):

  1. la esquina de la casilla a1  (la de la torre blanca del lado de la columna a)
  2. la esquina de la casilla h1  (la de la otra torre blanca)
  3. la esquina de la casilla h8
  4. la esquina de la casilla a8

Teclas: R = empezar de nuevo, Enter o Espacio = guardar (con las 4 marcadas), Q o Esc = salir sin guardar.
Al guardar muestra el tablero enderezado con la grilla para que verifiques que las líneas caen sobre las casillas.

Después de calibrar NO muevas la cámara ni el tablero. Si se mueven, volvé a correr este script.

Uso:
    python scripts/calibrar_esquinas_tablero.py
    python scripts/calibrar_esquinas_tablero.py --imagen foto.jpg     # calibrar sobre una foto ya guardada
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
from dotenv import load_dotenv

# Para que funcione corriéndolo directo (`python scripts/calibrar_esquinas_tablero.py`) y tome CAMARA_FUENTE del .env.
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
load_dotenv(RAIZ / ".env")

from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.tablero import (
    ARCHIVO_ESQUINAS,
    ORDEN_DE_CLICS,
    cargar_esquinas_calibradas,
    dibujar_grilla_debug,
    enderezar_tablero,
    guardar_esquinas_calibradas,
)

VENTANA = "Calibrar esquinas del tablero"


def _dibujar(foto, marcadas: list[tuple[int, int]]):
    lienzo = foto.copy()
    for i, (x, y) in enumerate(marcadas):
        cv2.circle(lienzo, (x, y), 6, (0, 0, 255), -1)
        cv2.putText(lienzo, ORDEN_DE_CLICS[i], (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    if len(marcadas) == 4:
        for i in range(4):
            cv2.line(lienzo, marcadas[i], marcadas[(i + 1) % 4], (0, 255, 0), 2)
        mensaje = "Enter = guardar | R = repetir | Q = salir"
    else:
        mensaje = f"Clic en la esquina de {ORDEN_DE_CLICS[len(marcadas)]} ({len(marcadas)}/4) | R = repetir | Q = salir"
    cv2.rectangle(lienzo, (0, 0), (lienzo.shape[1], 34), (0, 0, 0), -1)
    cv2.putText(lienzo, mensaje, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return lienzo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--imagen", help="usar esta foto en vez de capturar una de la cámara")
    args = parser.parse_args()

    foto = cv2.imread(args.imagen) if args.imagen else capturar_foto_tablero()
    if foto is None:
        raise SystemExit("No se pudo obtener la foto")

    marcadas: list[tuple[int, int]] = []

    def al_hacer_clic(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN and len(marcadas) < 4:
            marcadas.append((x, y))

    cv2.namedWindow(VENTANA, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(VENTANA, min(foto.shape[1], 1280), min(foto.shape[0], 720))
    cv2.setMouseCallback(VENTANA, al_hacer_clic)
    while True:
        cv2.imshow(VENTANA, _dibujar(foto, marcadas))
        tecla = cv2.waitKey(30) & 0xFF
        if tecla in (ord("q"), 27):
            print("Sin guardar.")
            break
        if tecla in (ord("r"), ord("R")):
            marcadas.clear()
        if tecla in (13, 32) and len(marcadas) == 4:
            guardar_esquinas_calibradas(dict(zip(ORDEN_DE_CLICS, marcadas)))
            plano = enderezar_tablero(foto, cargar_esquinas_calibradas())
            cv2.imwrite(str(ARCHIVO_ESQUINAS.with_name("tablero_enderezado.jpg")), dibujar_grilla_debug(plano))
            cv2.imwrite(str(ARCHIVO_ESQUINAS.with_name("foto_de_calibracion.jpg")), foto)
            print(f"Guardado en {ARCHIVO_ESQUINAS}")
            cv2.imshow("Tablero enderezado con la grilla (cualquier tecla para cerrar)", dibujar_grilla_debug(plano))
            cv2.waitKey(0)
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
