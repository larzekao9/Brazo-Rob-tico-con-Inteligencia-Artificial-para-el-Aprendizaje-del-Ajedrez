"""Detección geométrica del tablero en una foto (HU1, primera etapa).

Encuentra las 4 esquinas del tablero, endereza la perspectiva y divide el
resultado en sus 64 casillas. La clasificación de qué pieza hay en cada
casilla (segunda etapa de HU1) se agrega en un módulo aparte una vez que
esta parte esté validada contra fotos reales.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import cv2
import numpy as np

TAMANO_TABLERO_PLANO = 800  # píxeles de lado de la imagen ya enderezada
TAMANO_CASILLA = TAMANO_TABLERO_PLANO // 8

# `detectar_esquinas_tablero` encuentra el contorno de 4 lados más GRANDE de la
# imagen — en un tablero con borde ancho e impreso (letras/números alrededor
# del área de juego, ej. un tablero plegable tipo valija) eso agarra el borde
# de madera completo, no el área 8x8 real, y la grilla de `dividir_en_casillas`
# queda corrida respecto a las casillas reales (confirmado visualmente con
# `dibujar_grilla_debug` contra una foto real: con 0% de margen la grilla no
# coincide con las casillas, con ~7-9% sí). Config por variable de entorno
# (mismo patrón que `CAMARA_FUENTE`) para no tocar el comportamiento de
# tableros sin ese borde ancho si hiciera falta volver a 0.
MARGEN_TABLERO_PORCENTAJE = float(os.environ.get("MARGEN_TABLERO_PORCENTAJE", "7"))

# Con la cámara FIJA (en un trípode, por ejemplo) no hace falta detectar el tablero en cada foto: se marcan sus 4 esquinas una
# sola vez (`scripts/calibrar_esquinas_tablero.py`) y se guardan acá. Son las esquinas del ÁREA DE JUEGO (las casillas 8x8, sin
# el borde de madera), por eso con ellas el margen de recorte es 0. Es un archivo local de cada instalación: no se sube a git.
ARCHIVO_ESQUINAS = Path(
    os.environ.get("ESQUINAS_TABLERO_ARCHIVO", str(Path(__file__).resolve().parents[3] / "calibracion_local" / "esquinas_tablero.json"))
)
ORDEN_DE_CLICS = ("a1", "h1", "h8", "a8")
"""Esquinas del área de juego, nombradas por la casilla que las ocupa (así no importa hacia dónde esté girado el tablero en la foto)."""
ORDEN_DE_ENDEREZADO = ("a8", "h8", "h1", "a1")
"""Orden que espera `enderezar_tablero` (arriba-izq, arriba-der, abajo-der, abajo-izq del diagrama): blancas abajo, a8 arriba a la izquierda."""


def guardar_esquinas_calibradas(esquinas: dict[str, tuple[float, float]], ruta: Path | None = None) -> None:
    """Guarda las 4 esquinas marcadas (`{"a1": (x, y), "h1": ..., "h8": ..., "a8": ...}`, en píxeles de la foto)."""
    if set(esquinas) != set(ORDEN_DE_CLICS):
        raise ValueError(f"Hacen falta exactamente las esquinas {ORDEN_DE_CLICS}")
    destino = Path(ruta or ARCHIVO_ESQUINAS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({k: [float(v[0]), float(v[1])] for k, v in esquinas.items()}, indent=2), encoding="utf-8")


def cargar_esquinas_calibradas(ruta: Path | None = None) -> np.ndarray | None:
    """Esquinas guardadas, listas para `enderezar_tablero` (orden a8, h8, h1, a1), o `None` si todavía no se calibró.

    Raises:
        ValueError: si el archivo existe pero está dañado o incompleto.
    """
    origen = Path(ruta or ARCHIVO_ESQUINAS)
    if not origen.exists():
        return None
    try:
        datos = json.loads(origen.read_text(encoding="utf-8"))
        puntos = np.array([datos[nombre] for nombre in ORDEN_DE_ENDEREZADO], dtype=np.float32)
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"El archivo de esquinas {origen} está dañado: volvé a calibrar") from error
    if puntos.shape != (4, 2):
        raise ValueError(f"El archivo de esquinas {origen} está incompleto: volvé a calibrar")
    return puntos



def _ordenar_esquinas(puntos: np.ndarray) -> np.ndarray:
    """Ordena 4 puntos como (sup-izq, sup-der, inf-der, inf-izq).

    Trucos clásicos: la esquina superior-izquierda tiene la menor suma
    (x+y) y la inferior-derecha la mayor; la superior-derecha tiene la
    menor resta (x-y) y la inferior-izquierda la mayor.
    """
    suma = puntos.sum(axis=1)
    resta = np.diff(puntos, axis=1).flatten()
    ordenadas = np.zeros((4, 2), dtype=np.float32)
    ordenadas[0] = puntos[np.argmin(suma)]
    ordenadas[2] = puntos[np.argmax(suma)]
    ordenadas[1] = puntos[np.argmin(resta)]
    ordenadas[3] = puntos[np.argmax(resta)]
    return ordenadas


def detectar_esquinas_tablero(imagen: np.ndarray) -> np.ndarray:
    """Detecta las 4 esquinas del tablero (o del tapete que lo contiene).

    Busca el contorno de 4 lados más grande de la imagen — asume que el
    tablero es el objeto de mayor tamaño y contraste contra el fondo, algo
    razonable con una cámara fija apuntando de arriba hacia el tablero.

    Args:
        imagen: imagen BGR (la que devuelve `cv2.imread`).

    Returns:
        Array (4, 2) float32 con las esquinas en orden sup-izq, sup-der,
        inf-der, inf-izq.

    Raises:
        ValueError: si no se encuentra ningún contorno de 4 lados que ocupe
            una porción significativa de la imagen.
    """
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    difuminada = cv2.GaussianBlur(gris, (5, 5), 0)
    bordes = cv2.Canny(difuminada, 40, 120)
    bordes = cv2.dilate(bordes, np.ones((5, 5), np.uint8), iterations=2)

    contornos, _ = cv2.findContours(bordes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        raise ValueError("No se detectó ningún contorno en la imagen")

    area_imagen = imagen.shape[0] * imagen.shape[1]
    for contorno in sorted(contornos, key=cv2.contourArea, reverse=True):
        # El casco convexo elimina muescas hacia adentro (ej. la bisagra de un
        # tablero plegable, o una sombra) que si no rompen la aproximación a 4
        # lados — un tablero real siempre es un rectángulo convexo.
        casco = cv2.convexHull(contorno)
        perimetro = cv2.arcLength(casco, True)
        aproximado = cv2.approxPolyDP(casco, 0.03 * perimetro, True)
        if len(aproximado) == 4 and cv2.contourArea(aproximado) > 0.1 * area_imagen:
            return _ordenar_esquinas(aproximado.reshape(4, 2).astype(np.float32))

    raise ValueError("No se encontró un contorno de 4 esquinas que parezca un tablero")


def enderezar_tablero(
    imagen: np.ndarray, esquinas: np.ndarray, tamano: int = TAMANO_TABLERO_PLANO
) -> np.ndarray:
    """Aplica una transformación de perspectiva para ver el tablero de frente.

    Args:
        imagen: imagen original BGR.
        esquinas: las 4 esquinas del tablero, en el orden que devuelve
            `detectar_esquinas_tablero`.
        tamano: lado en píxeles de la imagen cuadrada resultante.

    Returns:
        Imagen BGR cuadrada de `tamano` x `tamano`, con el tablero ocupando
        todo el cuadro, visto de frente.
    """
    destino = np.array(
        [[0, 0], [tamano - 1, 0], [tamano - 1, tamano - 1], [0, tamano - 1]],
        dtype=np.float32,
    )
    matriz = cv2.getPerspectiveTransform(esquinas, destino)
    return cv2.warpPerspective(imagen, matriz, (tamano, tamano))


def dividir_en_casillas(
    tablero_plano: np.ndarray, margen_porcentaje: float = MARGEN_TABLERO_PORCENTAJE
) -> dict[str, np.ndarray]:
    """Divide la imagen ya enderezada del tablero en sus 64 casillas.

    Asume que la esquina superior-izquierda de `tablero_plano` es la casilla
    a8 y la inferior-derecha es h1 (orientación estándar de diagrama). Esta
    asunción depende de cómo se monte la cámara real y se ajusta una sola
    vez al calibrarla — no se recalcula en cada foto.

    Args:
        margen_porcentaje: recorta ese % de cada borde antes de dividir en
            8x8, para compensar tableros con borde ancho impreso (ver
            `MARGEN_TABLERO_PORCENTAJE`) — `detectar_esquinas_tablero` agarra
            el borde completo, no el área de juego, y sin este recorte la
            grilla queda corrida respecto a las casillas reales.

    Returns:
        Dict que mapea notación algebraica (ej. "e4") al recorte de imagen
        de esa casilla.
    """
    lado_original = tablero_plano.shape[0]
    margen = int(lado_original * margen_porcentaje / 100)
    if margen:
        tablero_plano = tablero_plano[margen : lado_original - margen, margen : lado_original - margen]
    lado = tablero_plano.shape[0]
    paso = lado // 8
    casillas: dict[str, np.ndarray] = {}
    for fila in range(8):
        for columna in range(8):
            nombre = f"{'abcdefgh'[columna]}{8 - fila}"
            casillas[nombre] = tablero_plano[
                fila * paso : (fila + 1) * paso,
                columna * paso : (columna + 1) * paso,
            ]
    return casillas


def dibujar_grilla_debug(tablero_plano: np.ndarray) -> np.ndarray:
    """Dibuja las líneas de la grilla 8x8 sobre una copia de la imagen.

    Solo para verificar visualmente que `enderezar_tablero` alineó bien el
    tablero — no se usa en el flujo real de reconocimiento.
    """
    debug = tablero_plano.copy()
    lado = tablero_plano.shape[0]
    paso = lado // 8
    for i in range(9):
        grosor = 3 if i in (0, 8) else 1
        cv2.line(debug, (i * paso, 0), (i * paso, lado), (0, 0, 255), grosor)
        cv2.line(debug, (0, i * paso), (lado, i * paso), (0, 0, 255), grosor)
    return debug


def imagen_control_ampliada(
    imagen: np.ndarray,
    esquinas: np.ndarray,
    margen_relativo: float = 0.12,
    tamano: int = TAMANO_TABLERO_PLANO,
    resaltar: tuple[str, ...] = (),
) -> np.ndarray:
    """Tablero enderezado con la grilla 8x8 y, alrededor, el marco y las letras/números que rodean el área de juego.

    `esquinas` son las del área de juego (en el orden de `enderezar_tablero`). El área de juego se dibuja centrada y ocupando
    `1 - 2 * margen_relativo` del lado; lo de afuera es la foto original (borde de madera, letras impresas). Sobre las líneas se
    rotulan columnas (a-h) y filas (8-1) como las usa el reconocimiento; `resaltar` marca en verde las casillas dadas. Solo para revisar a ojo; no se usa para reconocer.
    """
    borde = tamano * margen_relativo
    interior = tamano - 2 * borde
    destino = np.array(
        [[borde, borde], [tamano - borde, borde], [tamano - borde, tamano - borde], [borde, tamano - borde]], dtype=np.float32
    )
    matriz = cv2.getPerspectiveTransform(esquinas.astype(np.float32), destino)
    control = cv2.warpPerspective(imagen, matriz, (tamano, tamano))
    paso = interior / 8
    for i in range(9):
        grosor = 3 if i in (0, 8) else 1
        x = int(round(borde + i * paso))
        cv2.line(control, (x, int(borde)), (x, int(tamano - borde)), (0, 0, 255), grosor)
        cv2.line(control, (int(borde), x), (int(tamano - borde), x), (0, 0, 255), grosor)
    for nombre in resaltar:  # casillas que se van a guardar, en verde
        columna, fila = "abcdefgh".index(nombre[0]), 8 - int(nombre[1])
        x0, y0 = int(round(borde + columna * paso)), int(round(borde + fila * paso))
        cv2.rectangle(control, (x0, y0), (int(round(x0 + paso)), int(round(y0 + paso))), (0, 255, 0), 4)
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    for i in range(8):
        centro = int(round(borde + (i + 0.5) * paso))
        for texto, posicion in (
            ("abcdefgh"[i], (centro - 8, int(tamano - borde * 0.35))),
            ("abcdefgh"[i], (centro - 8, int(borde * 0.7))),
            (str(8 - i), (int(borde * 0.35), centro + 8)),
            (str(8 - i), (int(tamano - borde * 0.65), centro + 8)),
        ):
            cv2.putText(control, texto, posicion, fuente, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(control, texto, posicion, fuente, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    return control
