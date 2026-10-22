"""Geometría 3D del tablero: lente de cada cámara, su posición respecto del tablero y recortes que siguen el VOLUMEN de la pieza.

El problema de la altura: las esquinas calibradas dan una homografía exacta para lo que está APOYADO en la mesa, pero una pieza de 6 cm
se ve inclinada y su cabeza cae sobre las casillas vecinas. Con el lente conocido (distancia focal y distorsión) y las esquinas del tablero
(30 mm por casilla) se calcula dónde está la cámara (`solvePnP`) y, para cada casilla, dónde se proyecta la caja de 30 × 30 × 60 mm que
ocupa una pieza ahí. Recortar esa caja (en vez de la casilla plana con un margen fijo) deja siempre la pieza completa y centrada.

Sistema de coordenadas del tablero, en mm: origen en la esquina de a1, X hacia h (columnas), Y hacia la fila 8, Z hacia arriba. Las 4
esquinas se dan, como en toda la app, en el orden a1, h1, h8, a8.

El lente no se conoce de fábrica: `lente_supuesto` lo estima a partir de un campo de visión típico, y `autocalibrar_lente` lo mejora con
fotos del propio tablero (sus 7 × 7 esquinas internas son un patrón de calibración conocido): cuantas más fotos con el tablero movido o
inclinado, mejor. Se guarda un archivo por cámara en `calibracion_local/`.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

from backend.servicios.vision import tablero

LADO_CASILLA_MM = float(os.environ.get("CASILLA_MM", "30"))
ALTURA_PIEZA_MM = float(os.environ.get("ALTURA_REY_MM", "60"))
"""Altura de la pieza más alta (el rey): la caja que se recorta llega hasta ahí."""
LADO_TABLERO_MM = 8 * LADO_CASILLA_MM
FOV_HORIZONTAL_SUPUESTO = {"principal": 90.0, "secundaria": 65.0}
"""Campo de visión horizontal (grados) que se supone mientras el lente no esté calibrado: webcam gran angular y cámara de teléfono."""
ALTURA_BASE_MM = 8.0
"""Altura de la "huella" que se recorta para decidir si una casilla está ocupada: solo la base de la pieza, que apoya en la mesa y por eso
queda en su casilla aunque la cabeza se incline sobre otra."""
MARGEN_CAJA = 0.08
"""Margen (fracción del tamaño de la caja proyectada) que se agrega al recortarla."""
TAMANO_RECORTE = 96
ESQUINAS_INTERNAS = (7, 7)
"""Un tablero de 8 × 8 casillas tiene 7 × 7 esquinas internas."""
MINIMO_FOTOS_LENTE = 1

CORNERS_TABLERO_MM = np.array(
    [[0, 0, 0], [LADO_TABLERO_MM, 0, 0], [LADO_TABLERO_MM, LADO_TABLERO_MM, 0], [0, LADO_TABLERO_MM, 0]], dtype=np.float64
)
"""Esquinas a1, h1, h8, a8 en coordenadas del tablero."""


@dataclass
class Lente:
    """Parámetros del lente de una cámara para una resolución dada (la del cuadro que entrega la app)."""

    ancho: int
    alto: int
    fx: float
    fy: float
    cx: float
    cy: float
    distorsion: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0])
    origen: str = "supuesto"
    """`supuesto` (campo de visión típico), `autocalibrado` (con fotos del tablero) o `manual`."""
    error_px: float | None = None
    fotos: int = 0

    @property
    def matriz(self) -> np.ndarray:
        return np.array([[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]], dtype=np.float64)

    @property
    def coeficientes(self) -> np.ndarray:
        return np.array(self.distorsion, dtype=np.float64)

    @property
    def fov_horizontal(self) -> float:
        return math.degrees(2 * math.atan(self.ancho / (2 * self.fx)))


def lente_supuesto(ancho: int, alto: int, fov_horizontal: float = 70.0) -> Lente:
    """Lente sin distorsión, centrado, con el campo de visión horizontal dado."""
    f = (ancho / 2) / math.tan(math.radians(fov_horizontal) / 2)
    return Lente(ancho=ancho, alto=alto, fx=f, fy=f, cx=ancho / 2, cy=alto / 2)


# --- persistencia ---------------------------------------------------------------------------------------------------------
def archivo_lente(camara: str = "principal") -> Path:
    """Archivo del lente de `camara`, junto al de esquinas (así una prueba que redirija `tablero.ARCHIVO_ESQUINAS` aísla este también)."""
    return tablero.ARCHIVO_ESQUINAS.with_name(f"lente_{camara}.json")


def carpeta_fotos_lente(camara: str = "principal") -> Path:
    return tablero.ARCHIVO_ESQUINAS.with_name(f"lente_{camara}_fotos")


def guardar_lente(lente: Lente, camara: str = "principal") -> None:
    destino = archivo_lente(camara)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(asdict(lente), indent=2), encoding="utf-8")


def cargar_lente(camara: str, ancho: int, alto: int) -> Lente:
    """El lente guardado de `camara` si corresponde a esta resolución; si no, el supuesto para ese tamaño de imagen."""
    try:
        datos = json.loads(archivo_lente(camara).read_text(encoding="utf-8"))
        lente = Lente(**datos)
        if (lente.ancho, lente.alto) == (ancho, alto):
            return lente
    except (OSError, ValueError, TypeError):
        pass
    return lente_supuesto(ancho, alto, FOV_HORIZONTAL_SUPUESTO.get(camara, 70.0))


def borrar_lente(camara: str = "principal") -> None:
    archivo_lente(camara).unlink(missing_ok=True)
    for foto in carpeta_fotos_lente(camara).glob("*.jpg") if carpeta_fotos_lente(camara).is_dir() else []:
        foto.unlink(missing_ok=True)


# --- autocalibración del lente con el propio tablero ----------------------------------------------------------------------
def _puntos_del_patron() -> np.ndarray:
    """Las 7 × 7 esquinas internas del tablero en mm (en el orden de `findChessboardCorners`: fila por fila)."""
    columnas, filas = ESQUINAS_INTERNAS
    puntos = np.zeros((columnas * filas, 3), dtype=np.float32)
    puntos[:, :2] = np.mgrid[0:columnas, 0:filas].T.reshape(-1, 2) * LADO_CASILLA_MM
    return puntos


def detectar_esquinas_internas(imagen: np.ndarray) -> np.ndarray | None:
    """Las 49 esquinas internas del damero (`(49, 1, 2)`), o `None` si no se encuentran. Prueba el detector robusto y el clásico."""
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    encontrado, esquinas = cv2.findChessboardCornersSB(gris, ESQUINAS_INTERNAS, flags=cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY)
    if not encontrado:
        encontrado, esquinas = cv2.findChessboardCorners(gris, ESQUINAS_INTERNAS, flags=cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE)
        if encontrado:
            esquinas = cv2.cornerSubPix(gris, esquinas, (7, 7), (-1, -1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01))
    return esquinas.astype(np.float32) if encontrado else None


def autocalibrar_lente(imagenes: list[np.ndarray], camara: str = "principal") -> tuple[Lente, list[str]]:
    """Estima distancia focal y distorsión radial (k1, k2) con fotos del tablero y devuelve `(lente, avisos)`.

    El punto principal se deja en el centro y el aspecto en 1: con pocas fotos es lo que mantiene el problema bien planteado. Si el
    resultado no es plausible (focal fuera de rango, error grande, o cámara casi cenital sin perspectiva) se devuelve el lente supuesto y el
    motivo en `avisos`. Todas las imágenes deben tener la misma resolución.
    """
    avisos: list[str] = []
    if not imagenes:
        raise ValueError("Hacen falta fotos del tablero para calibrar el lente")
    alto, ancho = imagenes[0].shape[:2]
    detecciones = [(i, detectar_esquinas_internas(i)) for i in imagenes if i.shape[:2] == (alto, ancho)]
    validas = [e for _, e in detecciones if e is not None]
    if not validas:
        raise ValueError("No se encontraron las esquinas internas del tablero en ninguna foto: que se vea entero, parejo y sin piezas encima")
    base = lente_supuesto(ancho, alto, FOV_HORIZONTAL_SUPUESTO.get(camara, 70.0))
    puntos = [_puntos_del_patron() for _ in validas]
    banderas = (
        cv2.CALIB_USE_INTRINSIC_GUESS | cv2.CALIB_FIX_PRINCIPAL_POINT | cv2.CALIB_FIX_ASPECT_RATIO | cv2.CALIB_ZERO_TANGENT_DIST
        | cv2.CALIB_FIX_K3
    )
    try:
        error, matriz, distorsion, _, _ = cv2.calibrateCamera(puntos, validas, (ancho, alto), base.matriz.copy(), np.zeros(5), flags=banderas)
    except cv2.error as fallo:
        avisos.append(f"No se pudo calibrar el lente ({fallo}); se usa un campo de visión típico.")
        return base, avisos
    f = float(matriz[0, 0])
    plausible = 0.35 * ancho <= f <= 3.0 * ancho and error < 3.0
    if not plausible:
        avisos.append(
            f"El resultado no es confiable (focal {f:.0f} px, error {error:.1f} px): con la cámara casi cenital hay poca perspectiva. "
            "Agregá fotos con el tablero inclinado o movido, o dejá el lente supuesto."
        )
        return base, avisos
    if len(validas) < 3:
        avisos.append("Con menos de 3 fotos la estimación es aproximada: agregá fotos moviendo o inclinando el tablero.")
    lente = Lente(
        ancho=ancho, alto=alto, fx=f, fy=f, cx=ancho / 2, cy=alto / 2,
        distorsion=[float(d) for d in distorsion.ravel()[:5]] + [0.0] * (5 - len(distorsion.ravel()[:5])),
        origen="autocalibrado", error_px=round(float(error), 2), fotos=len(validas),
    )
    return lente, avisos


# --- pose y proyección ----------------------------------------------------------------------------------------------------
def pose_del_tablero(esquinas: np.ndarray, lente: Lente) -> tuple[np.ndarray, np.ndarray, float]:
    """Pose del tablero respecto de la cámara: `(rvec, tvec, error de reproyección en px)`.

    `esquinas` son las 4 esquinas en la imagen, en el orden a1, h1, h8, a8. Raises `ValueError` si no hay solución con el tablero delante
    de la cámara (señal de que las esquinas están espejadas o en otro orden).
    """
    imagen = np.asarray(esquinas, dtype=np.float64).reshape(4, 1, 2)
    ok, rvec, tvec = cv2.solvePnP(CORNERS_TABLERO_MM, imagen, lente.matriz, lente.coeficientes, flags=cv2.SOLVEPNP_IPPE)
    if not ok:
        raise ValueError("No se pudo calcular la posición de la cámara con esas esquinas")
    rotacion, _ = cv2.Rodrigues(rvec)
    centro_camara = tvec.ravel() + rotacion @ CORNERS_TABLERO_MM.mean(axis=0)
    if centro_camara[2] <= 0:
        raise ValueError("El tablero queda detrás de la cámara: las esquinas están espejadas o en otro orden")
    proyectadas, _ = cv2.projectPoints(CORNERS_TABLERO_MM, rvec, tvec, lente.matriz, lente.coeficientes)
    error = float(np.linalg.norm(proyectadas.reshape(4, 2) - imagen.reshape(4, 2), axis=1).mean())
    return rvec, tvec, error


def proyectar(puntos_mm: np.ndarray, rvec: np.ndarray, tvec: np.ndarray, lente: Lente) -> np.ndarray:
    """Puntos 3D del tablero (mm) -> píxeles de la imagen `(n, 2)`."""
    resultado, _ = cv2.projectPoints(np.asarray(puntos_mm, dtype=np.float64).reshape(-1, 3), rvec, tvec, lente.matriz, lente.coeficientes)
    return resultado.reshape(-1, 2)


def diagnostico(esquinas: np.ndarray, lente: Lente) -> dict:
    """Dónde está la cámara respecto del tablero: posición (mm, en coordenadas del tablero), distancia, inclinación y error."""
    rvec, tvec, error = pose_del_tablero(esquinas, lente)
    rotacion, _ = cv2.Rodrigues(rvec)
    posicion = (-rotacion.T @ tvec).ravel()  # centro de la cámara en el sistema del tablero
    eje_optico = rotacion.T @ np.array([0.0, 0.0, 1.0])  # hacia dónde mira, en el sistema del tablero
    inclinacion = math.degrees(math.acos(max(-1.0, min(1.0, -eje_optico[2]))))  # 0° = mira derecho hacia abajo
    return {
        "posicion_mm": [round(float(v), 1) for v in posicion],
        "altura_mm": round(float(posicion[2]), 1),
        "distancia_mm": round(float(np.linalg.norm(posicion - CORNERS_TABLERO_MM.mean(axis=0))), 1),
        "inclinacion_grados": round(inclinacion, 1),
        "error_px": round(error, 2),
    }


# --- recortes por volumen -------------------------------------------------------------------------------------------------
def _caja(columna: int, fila_tablero: int, alto_mm: float) -> np.ndarray:
    """Las 8 esquinas de la caja de 1 casilla × `alto_mm` sobre la casilla (`columna` 0 = a, `fila_tablero` 0 = fila 1), en mm."""
    x0, y0 = columna * LADO_CASILLA_MM, fila_tablero * LADO_CASILLA_MM
    base = [(x0, y0), (x0 + LADO_CASILLA_MM, y0), (x0 + LADO_CASILLA_MM, y0 + LADO_CASILLA_MM), (x0, y0 + LADO_CASILLA_MM)]
    return np.array([(x, y, 0.0) for x, y in base] + [(x, y, alto_mm) for x, y in base], dtype=np.float64)


def cajas_proyectadas(esquinas: np.ndarray, lente: Lente, alto_mm: float = ALTURA_PIEZA_MM) -> dict[str, np.ndarray]:
    """Para cada casilla (a8, b8 … h1, el orden de siempre) las 8 esquinas de su caja proyectadas en la imagen `(8, 2)`."""
    rvec, tvec, _ = pose_del_tablero(esquinas, lente)
    cajas = {}
    for fila_imagen in range(8):  # 0 = fila 8
        for columna in range(8):
            cajas[f"{'abcdefgh'[columna]}{8 - fila_imagen}"] = proyectar(_caja(columna, 7 - fila_imagen, alto_mm), rvec, tvec, lente)
    return cajas


def recortes_volumen(
    imagen: np.ndarray, esquinas: np.ndarray, lente: Lente, salida: int = TAMANO_RECORTE, alto_mm: float = ALTURA_PIEZA_MM
) -> dict[str, np.ndarray]:
    """Recorte de cada casilla que contiene la caja completa de la pieza (base + `alto_mm` de altura), de `salida` × `salida` píxeles.

    Se corta el rectángulo que envuelve a la caja proyectada, con un margen, de la imagen ORIGINAL (sin enderezar), se completa con borde
    replicado si se sale de la foto y se lleva a cuadrado sin deformar. Es el mismo recorte para entrenar y para reconocer.
    """
    alto_img, ancho_img = imagen.shape[:2]
    recortes: dict[str, np.ndarray] = {}
    for nombre, puntos in cajas_proyectadas(esquinas, lente, alto_mm).items():
        x0, y0 = puntos.min(axis=0)
        x1, y1 = puntos.max(axis=0)
        lado = max(x1 - x0, y1 - y0) * (1 + 2 * MARGEN_CAJA)  # cuadrado, centrado en la caja
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        izquierda, arriba = int(round(cx - lado / 2)), int(round(cy - lado / 2))
        lado_i = max(2, int(round(lado)))
        relleno = max(0, -izquierda, -arriba, izquierda + lado_i - ancho_img, arriba + lado_i - alto_img)
        if relleno:
            fuente = cv2.copyMakeBorder(imagen, relleno, relleno, relleno, relleno, cv2.BORDER_REPLICATE)
            izquierda, arriba = izquierda + relleno, arriba + relleno
        else:
            fuente = imagen
        recortes[nombre] = cv2.resize(fuente[arriba : arriba + lado_i, izquierda : izquierda + lado_i], (salida, salida), interpolation=cv2.INTER_AREA)
    return recortes


def recortes_base(
    imagen: np.ndarray, esquinas: np.ndarray, lente: Lente, salida: int = 64, alto_mm: float = ALTURA_BASE_MM
) -> dict[str, np.ndarray]:
    """Recorte de la HUELLA de cada casilla (la casilla y sus primeros `alto_mm` de altura), de `salida` × `salida` píxeles.

    Es la parte de la pieza que de verdad está en esa casilla: la cabeza de una pieza alta se desplaza por la perspectiva, la base no. Se usa para
    decidir si la casilla está vacía o con pieza blanca/negra, en vez de mirar toda la columna.
    """
    return recortes_volumen(imagen, esquinas, lente, salida=salida, alto_mm=alto_mm)


def dibujar_cajas(imagen: np.ndarray, esquinas: np.ndarray, lente: Lente, casillas: list[str] | None = None) -> np.ndarray:
    """La imagen con las cajas 3D de algunas casillas dibujadas encima (para comprobar a ojo que la geometría coincide con las piezas)."""
    salida = imagen.copy()
    cajas = cajas_proyectadas(esquinas, lente)
    elegidas = casillas or ["a1", "h1", "a8", "h8", "d4", "e5"]
    for nombre in elegidas:
        p = cajas[nombre].astype(int)
        for i in range(4):  # base, tapa y aristas verticales
            cv2.line(salida, tuple(p[i]), tuple(p[(i + 1) % 4]), (0, 255, 0), 2)
            cv2.line(salida, tuple(p[4 + i]), tuple(p[4 + (i + 1) % 4]), (0, 200, 255), 2)
            cv2.line(salida, tuple(p[i]), tuple(p[4 + i]), (255, 160, 0), 2)
    return salida
