"""Calibración unificada de las dos cámaras: comprueba que describen el MISMO tablero y con la misma orientación.

Cada cámara se calibra por separado marcando a1, h1, h8 y a8. Si las dos se marcaron igual, al enderezar la foto de cada una con sus esquinas
el tablero queda en el mismo lugar y con la misma orientación: la casilla e4 es el mismo cuadro en las dos. Aquí se comprueba comparando
las dos imágenes enderezadas (con el marco de madera y sus letras alrededor, que rompen la simetría del damero):

- **Orientación:** se prueba la imagen de la secundaria girada 0/90/180/270° y espejada; si otra versión se parece más a la principal que la
  original, la secundaria está calibrada girada o con las esquinas en otro orden.
- **Alineación:** la correlación de fase mide cuánto está corrida una imagen respecto de la otra (en píxeles y en casillas).
"""
from __future__ import annotations

import base64

import cv2
import numpy as np

from backend.servicios.vision.tablero import archivo_esquinas, cargar_esquinas_calibradas, enderezar_con_marco

TAMANO = 800
MARGEN_RELATIVO = 0.12
CASILLA_PX = TAMANO * (1 - 2 * MARGEN_RELATIVO) / 8
"""Lado de una casilla en la imagen enderezada (76 px)."""
ERROR_BIEN = 0.15
ERROR_REGULAR = 0.40
"""Error de alineación, en casillas: hasta ERROR_BIEN la calibración es buena, hasta ERROR_REGULAR se puede mejorar, y más es mala."""
MEJORA_MINIMA = 0.05
"""Cuánto más se tiene que parecer otra orientación que la original para decir que la cámara está girada."""

_TRANSFORMACIONES = [
    ("sin giro", 0, False), ("girada 90°", 90, False), ("girada 180°", 180, False), ("girada 270°", 270, False),
    ("espejada", 0, True), ("espejada y girada 90°", 90, True), ("espejada y girada 180°", 180, True), ("espejada y girada 270°", 270, True),
]
_GIROS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


def _aplicar(imagen: np.ndarray, giro: int, espejo: bool) -> np.ndarray:
    if espejo:
        imagen = cv2.flip(imagen, 1)
    return cv2.rotate(imagen, _GIROS[giro]) if giro else imagen


def _bordes(imagen_bgr: np.ndarray) -> np.ndarray:
    """Mapa de bordes suavizado: se parece entre cámaras aunque cambien la luz, el color y la exposición."""
    gris = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2GRAY)
    gris = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gris)
    gris = cv2.GaussianBlur(gris, (5, 5), 0).astype(np.float32)
    magnitud = cv2.magnitude(cv2.Sobel(gris, cv2.CV_32F, 1, 0), cv2.Sobel(gris, cv2.CV_32F, 0, 1))
    return cv2.GaussianBlur(magnitud, (9, 9), 0)


def _correlacion(a: np.ndarray, b: np.ndarray) -> float:
    return float(cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)[0, 0])


def _rotulo(imagen: np.ndarray, texto: str) -> np.ndarray:
    cv2.putText(imagen, texto, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(imagen, texto, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    return imagen


def _panel(principal: np.ndarray, secundaria: np.ndarray, diferencia: np.ndarray, lado: int = 400) -> np.ndarray:
    """Cuadrícula 2×2: principal, secundaria, las dos superpuestas (mitad y mitad) y el mapa de diferencia (rojo = no coinciden)."""
    mezcla = cv2.addWeighted(principal, 0.5, secundaria, 0.5, 0)
    paso = TAMANO * MARGEN_RELATIVO
    for i in range(9):  # grilla 8x8 de referencia sobre la mezcla
        x = int(round(paso + i * CASILLA_PX))
        cv2.line(mezcla, (x, int(paso)), (x, int(TAMANO - paso)), (255, 255, 255), 1)
        cv2.line(mezcla, (int(paso), x), (int(TAMANO - paso), x), (255, 255, 255), 1)
    calor = cv2.applyColorMap(cv2.normalize(diferencia, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8), cv2.COLORMAP_JET)
    paneles = [
        _rotulo(cv2.resize(imagen, (lado, lado)), texto)
        for imagen, texto in ((principal, "principal"), (secundaria, "secundaria"), (mezcla, "superpuestas"), (calor, "diferencia"))
    ]
    return np.vstack([np.hstack(paneles[:2]), np.hstack(paneles[2:])])


def comparar(foto_principal: np.ndarray, foto_secundaria: np.ndarray, esquinas_principal: np.ndarray, esquinas_secundaria: np.ndarray) -> dict:
    """Compara las dos fotos enderezadas con sus esquinas (orden de `enderezar_tablero`) y devuelve el informe y la imagen."""
    a = enderezar_con_marco(foto_principal, esquinas_principal, MARGEN_RELATIVO, TAMANO)
    b = enderezar_con_marco(foto_secundaria, esquinas_secundaria, MARGEN_RELATIVO, TAMANO)
    bordes_a = _bordes(a)
    puntajes = {nombre: _correlacion(bordes_a, _bordes(_aplicar(b, giro, espejo))) for nombre, giro, espejo in _TRANSFORMACIONES}
    mejor = max(puntajes, key=puntajes.get)
    original = puntajes["sin giro"]
    desorientada = mejor != "sin giro" and puntajes[mejor] > original + MEJORA_MINIMA

    # Alineación (con la secundaria ya en su mejor orientación, para medirla aunque esté girada).
    giro, espejo = next((g, e) for nombre, g, e in _TRANSFORMACIONES if nombre == mejor)
    b_orientada = _aplicar(b, giro, espejo) if desorientada else b
    ventana = cv2.createHanningWindow((TAMANO, TAMANO), cv2.CV_32F)
    (dx, dy), respuesta = cv2.phaseCorrelate(bordes_a, _bordes(b_orientada), ventana)
    error_px = float(np.hypot(dx, dy))
    error_casillas = error_px / CASILLA_PX

    diferencia = np.abs(bordes_a - _bordes(b)).astype(np.float32)
    imagen = _panel(a, b, diferencia)
    if desorientada:
        nivel = "orientacion"
        mensaje = (
            f"La cámara secundaria parece estar {mejor} respecto de la principal. Giró la imagen de la secundaria (Elegir cámaras → "
            "Girar la secundaria) o recalibrala marcando las esquinas en el mismo orden: a1, h1, h8 y a8 según las letras impresas."
        )
    elif error_casillas <= ERROR_BIEN:
        nivel = "bien"
        mensaje = f"Las dos calibraciones coinciden: el tablero queda alineado (error de {error_px:.0f} px, {error_casillas:.2f} casillas)."
    elif error_casillas <= ERROR_REGULAR:
        nivel = "regular"
        mensaje = f"Las calibraciones coinciden con un corrimiento de {error_px:.0f} px ({error_casillas:.2f} casillas). Funciona, pero se puede mejorar marcando las esquinas con más cuidado."
    else:
        nivel = "mal"
        mensaje = f"Las calibraciones no coinciden: el tablero queda corrido {error_px:.0f} px ({error_casillas:.2f} casillas). Recalibrá la cámara que tenga las esquinas peor puestas."
    exito, buffer = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not exito:
        raise RuntimeError("No se pudo codificar la imagen de la verificación")
    return {
        "nivel": nivel,
        "ok": nivel in ("bien", "regular"),
        "mensaje": mensaje,
        "error_px": round(error_px, 1),
        "error_casillas": round(error_casillas, 2),
        "orientacion": {"mejor": mejor, "puntajes": {nombre: round(v, 3) for nombre, v in puntajes.items()}},
        "imagen": base64.b64encode(buffer.tobytes()).decode("ascii"),
    }


def verificar(foto_principal: np.ndarray, foto_secundaria: np.ndarray) -> dict:
    """Como `comparar`, leyendo las esquinas calibradas de cada cámara.

    Raises:
        ValueError: si alguna de las dos cámaras no está calibrada.
    """
    esquinas = {}
    for camara in ("principal", "secundaria"):
        puntos = cargar_esquinas_calibradas(archivo_esquinas(camara))
        if puntos is None:
            raise ValueError(f"La cámara {camara} todavía no está calibrada")
        esquinas[camara] = puntos
    return comparar(foto_principal, foto_secundaria, esquinas["principal"], esquinas["secundaria"])
