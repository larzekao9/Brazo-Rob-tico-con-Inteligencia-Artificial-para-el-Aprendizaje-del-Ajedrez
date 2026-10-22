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
import numpy as np
from dotenv import load_dotenv

from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.modelo_piezas import CLASE_VACIA
from backend.servicios.vision.reconocimiento import esquinas_y_margen
from backend.servicios.vision.tablero import (
    dibujar_grilla_debug,
    dividir_en_casillas,
    enderezar_tablero,
    imagen_control_ampliada,
    recortes_ampliados,
)

CARPETA_DATASET = Path("training/dataset_propio")
def carpeta_ampliados() -> Path:
    """Los mismos recortes que `CARPETA_DATASET` pero ampliados (`tablero.recortes_ampliados`): `<nombre>_ampliado/<clase>/<id>_<casilla>.png`.

    Salen de los cuadros completos (`carpeta_cuadros()`) y se pueden volver a generar cuando cambia la geometría del recorte; con ellos
    se entrena el clasificador de piezas. Se guardan además para poder verlos y revisarlos como los recortes justos."""
    return CARPETA_DATASET.parent / f"{CARPETA_DATASET.name}_ampliado"


def carpeta_volumen() -> Path:
    """Como `carpeta_ampliados()` pero con el recorte por VOLUMEN (`geometria3d.recortes_volumen`): `<nombre>_volumen/<clase>/<id>_<casilla>.png`."""
    return CARPETA_DATASET.parent / f"{CARPETA_DATASET.name}_volumen"


def carpeta_cuadros() -> Path:
    """Carpeta hermana de `CARPETA_DATASET` (`<nombre>_cuadros`; así una prueba que redirija el dataset aísla también los cuadros)."""
    return CARPETA_DATASET.parent / f"{CARPETA_DATASET.name}_cuadros"


"""Foto COMPLETA de cada captura (`<id>.jpg`) y su manifiesto (`<id>.json`: esquinas y etiqueta de cada casilla): así se pueden volver a recortar\ncon otra geometría (`tablero.recortes_ampliados`) sin repetir las fotos. Fuera de `CARPETA_DATASET` para que no se tome por una clase."""

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


def _recortes_volumen(imagen: np.ndarray, esquinas: np.ndarray, camara: str) -> dict[str, np.ndarray]:
    """Recortes por volumen 3D con el lente de `camara` (el calibrado o el supuesto); `{}` si la geometría no se puede resolver."""
    from backend.servicios.vision import geometria3d

    try:
        alto, ancho = imagen.shape[:2]
        return geometria3d.recortes_volumen(imagen, np.asarray(esquinas)[::-1], geometria3d.cargar_lente(camara, ancho, alto))
    except ValueError:
        return {}


def _guardar_cuadro(
    marca: int, imagen: np.ndarray, esquinas: np.ndarray, ocupacion: dict[str, str], solo_piezas: bool, camara: str = "principal", grupo: str | None = None
) -> None:
    """Guarda la foto completa y el manifiesto de la captura `marca` (ver `carpeta_cuadros()`)."""
    import json

    destino = carpeta_cuadros()
    destino.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino / f"{marca}.jpg"), imagen, [cv2.IMWRITE_JPEG_QUALITY, 95])
    etiquetas = dict(ocupacion) if solo_piezas else {c: ocupacion.get(c, CLASE_VACIA) for c in (f"{f}{r}" for f in "abcdefgh" for r in "12345678")}
    (destino / f"{marca}.json").write_text(
        json.dumps(
            {
                "esquinas": [[float(x), float(y)] for x, y in np.asarray(esquinas)],
                "etiquetas": etiquetas,
                "camara": camara,
                "grupo": grupo or str(marca),  # las fotos de varias cámaras de un mismo instante comparten grupo
            }
        ),
        encoding="utf-8",
    )


def capturar_muestras(fen_piezas: str, ruta_imagen: str | None = None) -> int:
    """Guarda las 64 casillas ya etiquetadas de una foto del tablero real y devuelve cuántas se guardaron.

    Es la versión de siempre (solo el conteo); ver `capturar_muestras_con_id` para obtener también el id de la captura.
    """
    return capturar_muestras_con_id(fen_piezas, ruta_imagen)[1]


def capturar_muestras_con_id(
    fen_piezas: str,
    ruta_imagen: str | None = None,
    imagen: np.ndarray | None = None,
    solo_piezas: bool = False,
    camara: str = "principal",
    grupo: str | None = None,
) -> tuple[str, int]:
    """Guarda las 64 casillas ya etiquetadas de una foto del tablero real.

    Args:
        fen_piezas: qué pieza hay en cada casilla ocupada, en FEN de piezas.
        ruta_imagen: si se pasa, lee la foto de ese archivo (recomendado —
            una foto ya sacada con la cámara normal del celular). Si no,
            saca una foto nueva de la cámara en vivo configurada por
            `CAMARA_FUENTE`.
        imagen: foto ya decodificada (BGR); tiene prioridad sobre `ruta_imagen`
            y la cámara. La usa el endpoint de fotos subidas a mano.
        camara: de qué cámara es la foto (sus esquinas calibradas y su giro); `grupo`, id común de las fotos de un mismo instante.
        solo_piezas: si es True guarda únicamente las casillas ocupadas según el FEN (ninguna "vacia"); sirve para
            enseñar una clase de pieza sin inundar el dataset de casillas vacías.

    Returns:
        `(captura_id, guardadas)`: el id (solo dígitos, prefijo de los nombres
        de archivo de la captura, sirve para deshacerla) y la cantidad de
        casillas guardadas (64, salvo error de escritura).

    Raises:
        ValueError: si `fen_piezas` es inválido, si `solo_piezas` y el FEN no tiene ninguna pieza, si `ruta_imagen` no se pudo
            leer, o si no se detectó el tablero en la foto (mismo error que
            `detectar_esquinas_tablero`).
        RuntimeError: si no se pudo capturar la foto (cámara en vivo).
    """
    ocupacion_esperada = fen_piezas_a_ocupacion(fen_piezas)
    if solo_piezas and not ocupacion_esperada:
        raise ValueError("Con solo_piezas el FEN debe tener al menos una pieza")

    if imagen is not None:
        pass
    elif ruta_imagen is not None:
        print(f"Leyendo foto: {ruta_imagen}")
        imagen = cv2.imread(ruta_imagen)
        if imagen is None:
            raise ValueError(f"No se pudo leer la imagen: {ruta_imagen}")
    else:
        print("Sacando foto (misma cámara configurada por CAMARA_FUENTE)...")
        imagen = capturar_foto_tablero(camara=camara)

    esquinas, margen = esquinas_y_margen(imagen, camara)  # las esquinas calibradas de la cámara fija, si existen
    plano = enderezar_tablero(imagen, esquinas)

    CARPETA_DATASET.mkdir(parents=True, exist_ok=True)
    ruta_control = CARPETA_DATASET / "_ultima_captura.jpg"
    # Con esquinas calibradas (margen 0) la imagen de control incluye el marco y las letras que rodean el área de juego.
    control = imagen_control_ampliada(imagen, esquinas) if not margen else dibujar_grilla_debug(plano)
    cv2.imwrite(str(ruta_control), control)
    print(f"Imagen de control guardada en {ruta_control} — revisala antes de confiar en las casillas.")

    casillas = dividir_en_casillas(plano, margen)

    marca_tiempo = time.time_ns() // 1_000_000
    if not margen:  # solo con esquinas calibradas el recorte ampliado tiene sentido
        _guardar_cuadro(marca_tiempo, imagen, esquinas, ocupacion_esperada, solo_piezas, camara, grupo)
    ampliados = recortes_ampliados(imagen, esquinas) if not margen else {}
    volumen = _recortes_volumen(imagen, esquinas, camara) if not margen else {}
    guardadas = 0
    for nombre_casilla, recorte in casillas.items():
        if solo_piezas and nombre_casilla not in ocupacion_esperada:
            continue
        clase = ocupacion_esperada.get(nombre_casilla, CLASE_VACIA)
        carpeta_clase = CARPETA_DATASET / clase
        carpeta_clase.mkdir(parents=True, exist_ok=True)
        ruta = carpeta_clase / f"{marca_tiempo}_{nombre_casilla}.png"
        if cv2.imwrite(str(ruta), recorte):
            guardadas += 1
            if nombre_casilla in ampliados:
                destino_ampliado = carpeta_ampliados() / clase
                destino_ampliado.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(destino_ampliado / f"{marca_tiempo}_{nombre_casilla}.png"), ampliados[nombre_casilla])
            if nombre_casilla in volumen:
                destino_volumen = carpeta_volumen() / clase
                destino_volumen.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(destino_volumen / f"{marca_tiempo}_{nombre_casilla}.png"), volumen[nombre_casilla])
    return str(marca_tiempo), guardadas


if __name__ == "__main__":
    load_dotenv()  # CAMARA_FUENTE y CAMARA_API del .env
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
