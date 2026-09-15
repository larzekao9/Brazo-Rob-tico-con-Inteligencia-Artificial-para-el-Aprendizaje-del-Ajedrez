"""Arma un dataset de casillas etiquetadas con fotos reales de TU tablero.

El clasificador (`training/entrenar_clasificador_piezas.py`) se entrenó con
el dataset público de Roboflow — piezas y colores de tablero distintos a los
de tu tablero real. Cuando el tablero real es visualmente muy distinto,
`clasificar_pieza` puede fallar sistemáticamente aunque la geometría
(`detectar_esquinas_tablero`) esté perfecta — son dos problemas separados.

Esto arma un dataset de tu tablero específico, sin anotar nada a mano: vos
armás una posición conocida (le decís al script qué pieza hay en cada
casilla que ocupaste, en notación FEN de piezas), sacás la foto, y cada una
de las 64 casillas queda guardada ya etiquetada.

No hace falta que la posición sea una partida legal — de hecho conviene que
NO lo sea: en una partida normal solo hay 1 dama y 1 rey por color, así que
para juntar más ejemplos de esas piezas (las que menos aparecen) podés armar
posiciones "imposibles" a propósito, con varias damas o reyes de cada color
repartidos por el tablero.

Uso:
    python -m training.capturar_dataset_propio "<fen_de_piezas>"

Ejemplo (posición inicial estándar):
    python -m training.capturar_dataset_propio "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

Corré esto varias veces — cambiando el ángulo del celular y/o la posición de
las piezas entre foto y foto — para juntar variedad antes de reentrenar con
`training/reentrenar_con_dataset_propio.py`.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2

from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.modelo_piezas import CLASE_VACIA
from backend.servicios.vision.tablero import detectar_esquinas_tablero, dividir_en_casillas, enderezar_tablero

CARPETA_DATASET = Path("training/dataset_propio")

_LETRA_A_TIPO = {
    "p": "pawn", "n": "knight", "b": "bishop", "r": "rook", "q": "queen", "k": "king",
}


def fen_piezas_a_ocupacion(fen_piezas: str) -> dict[str, str]:
    """Convierte el primer campo de un FEN (ubicación de piezas) a `{casilla: clase}`.

    Args:
        fen_piezas: solo el campo de ubicación de piezas (ej.
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"), no el FEN completo.

    Raises:
        ValueError: si el formato no tiene 8 filas de 8 columnas cada una,
            o si aparece un carácter que no es ni dígito ni letra de pieza.
    """
    ocupacion: dict[str, str] = {}
    filas = fen_piezas.strip().split("/")
    if len(filas) != 8:
        raise ValueError(f"Se esperaban 8 filas separadas por '/', hay {len(filas)}: {fen_piezas!r}")

    for indice_fila, fila in enumerate(filas):
        numero_fila = 8 - indice_fila
        columna = 0
        for caracter in fila:
            if caracter.isdigit():
                columna += int(caracter)
                continue
            tipo = _LETRA_A_TIPO.get(caracter.lower())
            if tipo is None:
                raise ValueError(f"Carácter de pieza inválido: {caracter!r} en la fila {fila!r}")
            color = "white" if caracter.isupper() else "black"
            casilla = f"{'abcdefgh'[columna]}{numero_fila}"
            ocupacion[casilla] = f"{color}-{tipo}"
            columna += 1
        if columna != 8:
            raise ValueError(f"La fila {indice_fila} no suma 8 columnas ({columna}): {fila!r}")
    return ocupacion


def capturar_muestras(fen_piezas: str) -> int:
    """Saca una foto del tablero real y guarda sus 64 casillas ya etiquetadas.

    Returns:
        Cantidad de casillas guardadas (64, salvo error de escritura).

    Raises:
        ValueError: si `fen_piezas` es inválido, o si no se detectó el
            tablero en la foto (mismo error que `detectar_esquinas_tablero`).
        RuntimeError: si no se pudo capturar la foto (cámara).
    """
    ocupacion_esperada = fen_piezas_a_ocupacion(fen_piezas)

    print("Sacando foto (misma cámara configurada por CAMARA_FUENTE)...")
    imagen = capturar_foto_tablero()
    esquinas = detectar_esquinas_tablero(imagen)
    plano = enderezar_tablero(imagen, esquinas)
    casillas = dividir_en_casillas(plano)

    marca_tiempo = int(time.time())
    guardadas = 0
    for nombre_casilla, recorte in casillas.items():
        clase = ocupacion_esperada.get(nombre_casilla, CLASE_VACIA)
        carpeta_clase = CARPETA_DATASET / clase
        carpeta_clase.mkdir(parents=True, exist_ok=True)
        ruta = carpeta_clase / f"{marca_tiempo}_{nombre_casilla}.png"
        if cv2.imwrite(str(ruta), recorte):
            guardadas += 1
    return guardadas


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Uso: python -m training.capturar_dataset_propio "<fen_de_piezas>"')
        print('Ejemplo: python -m training.capturar_dataset_propio "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"')
        sys.exit(1)
    try:
        cantidad = capturar_muestras(sys.argv[1])
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}")
        sys.exit(1)
    print(f"Guardadas {cantidad} casillas en {CARPETA_DATASET}/")
