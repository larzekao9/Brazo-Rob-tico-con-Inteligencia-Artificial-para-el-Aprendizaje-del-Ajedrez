"""En qué casilla hay una pieza, comparando la foto con la del tablero VACÍO (sin modelo entrenado).

Cada cámara guarda una foto de referencia del tablero vacío ya enderezado (visto de frente, 800 × 800). Para una foto nueva se endereza igual
y se mide, en el centro de cada casilla, cuánto cambió el color (en LAB, que separa luz de color): la casilla con la pieza es la que más
cambia. Restando el "fondo" (el percentil 25 de las 64 casillas), un cambio de luz parejo en todo el tablero no cuenta.

La casilla la decide la cámara MENOS inclinada (la que mira más desde arriba): ahí la pieza tapa solo su casilla. En una cámara en diagonal
la cabeza de una pieza alta cae sobre la casilla de al lado y "también cambia", así que esa cámara solo se usa si no hay otra. Con las fotos
reales: la cámara casi cenital acertó 30 de 30 (la casilla de la pieza cambia 13 veces más que la segunda) y la diagonal 27 de 30.

La referencia se guarda al capturar «Casilla vacía» (`dataset_propio.capturar_foto_etiquetada`); si cambia mucho la luz, se vuelve a capturar.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from backend.servicios.vision import tablero

LADO = 800
CASILLA = LADO // 8
CENTRO = (20, 80)
"""Parte de la casilla (en píxeles de los 100 de cada una) que se compara: el centro, sin los bordes, que cambian con un error chico de calibración."""
MINIMO_PIEZA = 15.0
"""Cambio mínimo (sobre el fondo del tablero) para decir que hay una pieza. Con fotos reales: el tablero vacío cambia como mucho 3,5 en la
cámara de arriba y 12 en la diagonal; una pieza, 24 o más."""
RELACION_MINIMA = 2.0
"""Cuántas veces más tiene que cambiar la casilla ganadora que la segunda para no ser "ambigua" (hay otra pieza o una mano)."""
NOMBRES = [f"{c}{f}" for f in range(8, 0, -1) for c in "abcdefgh"]
"""Orden de las casillas: a8, b8 … h1 (el mismo que `captura_estable.NOMBRES`)."""


def ruta_referencia(camara: str = "principal") -> Path:
    """Foto de referencia de `camara`, junto a sus esquinas (así una prueba que redirija `tablero.ARCHIVO_ESQUINAS` la aísla)."""
    return tablero.ARCHIVO_ESQUINAS.with_name(f"vacio_{camara}.png")


def _enderezada(imagen: np.ndarray, esquinas: np.ndarray) -> np.ndarray:
    return tablero.enderezar_tablero(imagen, np.asarray(esquinas, dtype=np.float32), LADO)


def _lab(enderezada: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(cv2.cvtColor(enderezada, cv2.COLOR_BGR2LAB), (5, 5), 0).astype(np.float32)


def guardar_referencia(camara: str, fotos: list[tuple[np.ndarray, np.ndarray]]) -> None:
    """Guarda la referencia del tablero vacío de `camara`: la mediana de `fotos` (`(imagen, esquinas en el orden de enderezar_tablero)`)."""
    if not fotos:
        raise ValueError("Hace falta al menos una foto del tablero vacío")
    enderezadas = np.stack([_enderezada(imagen, esquinas) for imagen, esquinas in fotos])
    destino = ruta_referencia(camara)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), np.median(enderezadas, axis=0).astype(np.uint8))


_referencias: dict[Path, tuple[tuple[int, int], np.ndarray]] = {}
_lab_de_referencias: dict[int, tuple[np.ndarray, np.ndarray]] = {}


def cargar_referencia(camara: str = "principal") -> np.ndarray | None:
    """La referencia de `camara` (enderezada, BGR), o `None` si todavía no se guardó.

    Se lee del disco solo cuando el archivo cambia (fecha o tamaño): en el video en vivo se pide en cada cuadro. El arreglo devuelto es
    compartido, no hay que modificarlo.
    """
    ruta = ruta_referencia(camara)
    try:
        estado = ruta.stat()
    except FileNotFoundError:
        _referencias.pop(ruta, None)
        return None
    marca = (estado.st_mtime_ns, estado.st_size)
    guardada = _referencias.get(ruta)
    if guardada is None or guardada[0] != marca:
        imagen = cv2.imread(str(ruta))
        if imagen is None:
            return None
        _referencias[ruta] = guardada = (marca, imagen)
    return guardada[1]


def _lab_de_referencia(referencia: np.ndarray) -> np.ndarray:
    """`_lab(referencia)` guardado mientras sea el mismo arreglo (el de `cargar_referencia`), para no recalcularlo en cada cuadro."""
    guardado = _lab_de_referencias.get(id(referencia))
    if guardado is None or guardado[0] is not referencia:
        if len(_lab_de_referencias) > 8:
            _lab_de_referencias.clear()
        guardado = _lab_de_referencias[id(referencia)] = (referencia, _lab(referencia))
    return guardado[1]


PERCENTIL_FONDO = 25
"""Qué percentil de los cambios de las 64 casillas se toma como "fondo" (luz) y se resta. Con la posición inicial hay 32 casillas vacías: el
percentil 25 siempre cae en una vacía (la mediana, con más de 32 piezas, caería en una ocupada)."""


def puntajes(imagen: np.ndarray, esquinas: np.ndarray, referencia: np.ndarray) -> np.ndarray:
    """Cuánto cambió cada casilla (`(64,)`, orden `NOMBRES`) respecto de la referencia, ya restado el fondo (`PERCENTIL_FONDO`)."""
    diferencia = np.abs(_lab(_enderezada(imagen, esquinas)) - _lab_de_referencia(referencia)).sum(axis=2)
    desde, hasta = CENTRO
    cambios = np.array(
        [diferencia[f * CASILLA + desde : f * CASILLA + hasta, c * CASILLA + desde : c * CASILLA + hasta].mean() for f in range(8) for c in range(8)]
    )
    return cambios - np.percentile(cambios, PERCENTIL_FONDO)


def decidir(cambios: np.ndarray) -> tuple[str | None, str, float]:
    """`(casilla, estado, confianza)` de una pieza sola a partir de `puntajes`: estado `"ok"`, `"ninguna"` o `"ambigua"` (casilla `None`)."""
    orden = np.argsort(cambios)[::-1]
    mejor, segunda = float(cambios[orden[0]]), max(float(cambios[orden[1]]), 0.0)
    if mejor < MINIMO_PIEZA:
        return None, "ninguna", 0.0
    confianza = 1.0 - segunda / mejor
    if segunda * RELACION_MINIMA > mejor:
        return None, "ambigua", confianza
    return NOMBRES[int(orden[0])], "ok", confianza


def _inclinacion(camara: str, imagen: np.ndarray, esquinas: np.ndarray) -> float:
    """Cuánto se inclina la cámara respecto de la vertical (0° = mira derecho hacia abajo); 90 si no se puede calcular."""
    from backend.servicios.vision import geometria3d

    alto, ancho = imagen.shape[:2]
    try:
        return float(geometria3d.diagnostico(np.asarray(esquinas)[::-1], geometria3d.cargar_lente(camara, ancho, alto))["inclinacion_grados"])
    except ValueError:
        return 90.0


def _cambios_por_camara(fotos: dict[str, np.ndarray]) -> dict[str, tuple[np.ndarray, float]]:
    """`{camara: (puntajes, inclinación)}` de las cámaras de `fotos` que tienen esquinas calibradas y referencia."""
    lecturas = {}
    for camara, imagen in fotos.items():
        referencia = cargar_referencia(camara)
        esquinas = tablero.cargar_esquinas_calibradas(tablero.archivo_esquinas(camara))
        if referencia is None or esquinas is None:
            continue
        lecturas[camara] = (puntajes(imagen, esquinas, referencia), _inclinacion(camara, imagen, esquinas))
    return lecturas


def detectar_casilla(fotos: dict[str, np.ndarray]) -> tuple[str | None, str, float, dict[str, str]] | None:
    """La casilla de la pieza sola en `fotos` (`{camara: imagen}`) por diferencia con el tablero vacío.

    Usa las cámaras que tienen esquinas calibradas y referencia; decide la menos inclinada. Devuelve `(casilla, estado, confianza, por_camara)`
    (`por_camara`: la casilla que ve cada una, `""` si ninguna clara), o `None` si ninguna cámara tiene referencia (se usa otro método).
    """
    lecturas = _cambios_por_camara(fotos)
    if not lecturas:
        return None
    decisora = min(lecturas, key=lambda camara: lecturas[camara][1])
    decisiones = {camara: decidir(cambios) for camara, (cambios, _) in lecturas.items()}
    casilla, estado, confianza = decisiones[decisora]
    return casilla, estado, confianza, {camara: decision[0] or "" for camara, decision in decisiones.items()}


def ocupadas(fotos: dict[str, np.ndarray]) -> tuple[np.ndarray, str] | None:
    """Qué casillas tienen pieza (`(64,)` bool, orden `NOMBRES`) según la cámara menos inclinada de `fotos`, con cualquier cantidad de piezas.

    Una casilla está ocupada si cambió `MINIMO_PIEZA` o más respecto del tablero vacío. Devuelve `(ocupadas, camara que decidió)`, o `None` si
    ninguna cámara tiene referencia.
    """
    lecturas = _cambios_por_camara(fotos)
    if not lecturas:
        return None
    decisora = min(lecturas, key=lambda camara: lecturas[camara][1])
    return lecturas[decisora][0] >= MINIMO_PIEZA, decisora
