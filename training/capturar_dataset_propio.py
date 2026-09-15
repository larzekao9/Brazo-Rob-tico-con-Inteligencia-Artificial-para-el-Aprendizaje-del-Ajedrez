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

No hace falta elegir en qué carpeta va cada foto ni nada parecido — el
script arma solo las 64 casillas ya separadas por clase a partir de UNA
sola foto del tablero completo más el FEN que le pasás.

Dos formas de usarlo:

1) Con una foto que ya sacaste (RECOMENDADO): sacá la foto con la cámara
   normal del celular (mejor calidad, sin apuro, tablero quieto — nada de
   cámara virtual en vivo, que puede sacar la foto mientras todavía estás
   moviendo el celular). Pasala a la compu (por cable, WhatsApp a vos
   mismo, Google Fotos, lo que uses) y corré:

       python -m training.capturar_dataset_propio "<fen_de_piezas>" "<ruta_a_la_foto.jpg>"

2) Con la cámara en vivo configurada por CAMARA_FUENTE (más rápido pero
   más frágil — ver el problema de timing más arriba):

       python -m training.capturar_dataset_propio "<fen_de_piezas>"

Ejemplo (posición inicial estándar, foto ya sacada):
    python -m training.capturar_dataset_propio "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR" "C:/Users/USUARIO/Downloads/tablero1.jpg"

Cada corrida también guarda `training/dataset_propio/_ultima_captura.jpg`
(el tablero ya enderezado, con la grilla 8x8 dibujada encima) — ABRILA
SIEMPRE antes de confiar en las 64 casillas que se acaban de guardar. Si
esa imagen sale borrosa, cortada, o mal alineada con la grilla, las
casillas de esa corrida tampoco sirven — borralas de
`training/dataset_propio/` (buscá por la marca de tiempo en el nombre del
archivo, todas empiezan igual) y repetí la captura.

Corré esto varias veces — cambiando el ángulo y/o la posición de las
piezas entre foto y foto — para juntar variedad antes de reentrenar con
`training/reentrenar_con_dataset_propio.py`.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2

from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.modelo_piezas import CLASE_VACIA
from backend.servicios.vision.tablero import (
    detectar_esquinas_tablero,
    dibujar_grilla_debug,
    dividir_en_casillas,
    enderezar_tablero,
)

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


def capturar_muestras(fen_piezas: str, ruta_imagen: str | None = None) -> int:
    """Guarda las 64 casillas ya etiquetadas de una foto del tablero real.

    Args:
        fen_piezas: qué pieza hay en cada casilla ocupada, en FEN de piezas.
        ruta_imagen: si se pasa, lee la foto de ese archivo (recomendado —
            una foto ya sacada con la cámara normal del celular). Si no,
            saca una foto nueva de la cámara en vivo configurada por
            `CAMARA_FUENTE`.

    Returns:
        Cantidad de casillas guardadas (64, salvo error de escritura).

    Raises:
        ValueError: si `fen_piezas` es inválido, si `ruta_imagen` no se pudo
            leer, o si no se detectó el tablero en la foto (mismo error que
            `detectar_esquinas_tablero`).
        RuntimeError: si no se pudo capturar la foto (cámara en vivo).
    """
    ocupacion_esperada = fen_piezas_a_ocupacion(fen_piezas)

    if ruta_imagen is not None:
        print(f"Leyendo foto: {ruta_imagen}")
        imagen = cv2.imread(ruta_imagen)
        if imagen is None:
            raise ValueError(f"No se pudo leer la imagen: {ruta_imagen}")
    else:
        print("Sacando foto (misma cámara configurada por CAMARA_FUENTE)...")
        imagen = capturar_foto_tablero()

    esquinas = detectar_esquinas_tablero(imagen)
    plano = enderezar_tablero(imagen, esquinas)

    CARPETA_DATASET.mkdir(parents=True, exist_ok=True)
    ruta_control = CARPETA_DATASET / "_ultima_captura.jpg"
    cv2.imwrite(str(ruta_control), dibujar_grilla_debug(plano))
    print(f"Imagen de control guardada en {ruta_control} — revisala antes de confiar en las casillas.")

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
    if len(sys.argv) not in (2, 3):
        print('Uso: python -m training.capturar_dataset_propio "<fen_de_piezas>" ["<ruta_a_la_foto.jpg>"]')
        print('Ejemplo: python -m training.capturar_dataset_propio "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR" "C:/fotos/tablero1.jpg"')
        sys.exit(1)
    try:
        cantidad = capturar_muestras(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}")
        sys.exit(1)
    print(f"Guardadas {cantidad} casillas en {CARPETA_DATASET}/")
