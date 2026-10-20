"""Calibración de la cámara fija (proceso A del PLAN_CAMARA.md): calidad de las esquinas marcadas, metadata de la sesión
(resolución, cámara, fecha), vigencia y detección de que la cámara se movió.

Las esquinas siguen guardándose donde las lee el reconocimiento (`tablero.ARCHIVO_ESQUINAS`); al lado van dos archivos
con el mismo nombre base: `<nombre>.meta.json` (metadata) y `<nombre>.referencia.jpg` (la foto sobre la que se marcó).
Las rutas salen de `tablero.ARCHIVO_ESQUINAS` en cada llamada, así que una prueba que lo redirija a una carpeta temporal
aísla también estos archivos.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from backend.servicios.vision import tablero

AREA_MINIMA_RELATIVA = 0.05
"""Debajo de esta fracción de la foto el tablero se ve demasiado chico para reconocer piezas."""
RELACION_ASPECTO_ACEPTABLE = (0.5, 2.0)
"""Ancho/alto medios del cuadrilátero en la foto; con cámara inclinada se deforma, pero fuera de este rango algo está mal."""
RELACION_LADOS_OPUESTOS_MAXIMA = 2.0
ANGULO_INTERNO_ACEPTABLE = (45.0, 135.0)
MARGEN_BORDE_RELATIVO = 0.01

MINIMO_COINCIDENCIAS = 12
"""Coincidencias de ORB que sobreviven a RANSAC para poder fiarse de la comparación."""
UMBRAL_DESPLAZAMIENTO_PX = 6.0
"""Desplazamiento máximo (en píxeles) de una esquina del tablero a partir del cual se considera que la cámara se movió."""


def ruta_metadata() -> Path:
    """Archivo de metadata junto al de esquinas."""
    return tablero.ARCHIVO_ESQUINAS.with_suffix(".meta.json")


def ruta_referencia() -> Path:
    """Foto de referencia junto al archivo de esquinas."""
    return tablero.ARCHIVO_ESQUINAS.with_suffix(".referencia.jpg")


def _distancia(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angulo_interno(anterior: tuple[float, float], vertice: tuple[float, float], siguiente: tuple[float, float]) -> float:
    ux, uy = anterior[0] - vertice[0], anterior[1] - vertice[1]
    vx, vy = siguiente[0] - vertice[0], siguiente[1] - vertice[1]
    norma = math.hypot(ux, uy) * math.hypot(vx, vy)
    if norma == 0:
        return 0.0
    coseno = max(-1.0, min(1.0, (ux * vx + uy * vy) / norma))
    return math.degrees(math.acos(coseno))


def evaluar_calidad(puntos: dict[str, tuple[float, float]], resolucion: tuple[int, int] | None = None) -> list[str]:
    """Advertencias (no errores) sobre cuatro esquinas ya válidas (convexas, en orden a1, h1, h8, a8).

    Args:
        puntos: `{"a1": (x, y), "h1": ..., "h8": ..., "a8": ...}` en píxeles de la foto.
        resolucion: `(ancho, alto)` de la foto; habilita las advertencias de tamaño y de esquinas pegadas al borde.

    Returns:
        Mensajes en español; vacío si la calibración se ve bien.
    """
    ciclo = [puntos[nombre] for nombre in tablero.ORDEN_DE_CLICS]
    lado_a1_h1 = _distancia(ciclo[0], ciclo[1])
    lado_h1_h8 = _distancia(ciclo[1], ciclo[2])
    lado_h8_a8 = _distancia(ciclo[2], ciclo[3])
    lado_a8_a1 = _distancia(ciclo[3], ciclo[0])
    advertencias: list[str] = []

    horizontal = (lado_a1_h1 + lado_h8_a8) / 2
    vertical = (lado_h1_h8 + lado_a8_a1) / 2
    if vertical > 0 and not RELACION_ASPECTO_ACEPTABLE[0] <= horizontal / vertical <= RELACION_ASPECTO_ACEPTABLE[1]:
        advertencias.append(
            "El tablero se ve muy deformado (mucho más ancho que alto, o al revés): revisá que las esquinas estén bien marcadas."
        )
    for par, nombre in (((lado_a1_h1, lado_h8_a8), "a1-h1 y h8-a8"), ((lado_h1_h8, lado_a8_a1), "h1-h8 y a8-a1")):
        menor, mayor = min(par), max(par)
        if menor == 0 or mayor / menor > RELACION_LADOS_OPUESTOS_MAXIMA:
            advertencias.append(
                f"Los lados {nombre} son muy distintos: la cámara está muy inclinada o alguna esquina quedó mal puesta."
            )
    angulos = [_angulo_interno(ciclo[i - 1], ciclo[i], ciclo[(i + 1) % 4]) for i in range(4)]
    if any(not ANGULO_INTERNO_ACEPTABLE[0] <= angulo <= ANGULO_INTERNO_ACEPTABLE[1] for angulo in angulos):
        advertencias.append("Algún ángulo del cuadrilátero es muy agudo u obtuso: revisá el orden y la posición de las esquinas.")

    if resolucion is not None:
        ancho, alto = resolucion
        area_doble = sum(
            ciclo[i][0] * ciclo[(i + 1) % 4][1] - ciclo[(i + 1) % 4][0] * ciclo[i][1] for i in range(4)
        )
        if abs(area_doble) / 2 < AREA_MINIMA_RELATIVA * ancho * alto:
            advertencias.append("El tablero ocupa muy poco de la foto: acercá la cámara o el tablero para reconocer mejor las piezas.")
        margen_x, margen_y = ancho * MARGEN_BORDE_RELATIVO, alto * MARGEN_BORDE_RELATIVO
        if any(x < margen_x or y < margen_y or x > ancho - margen_x or y > alto - margen_y for x, y in ciclo):
            advertencias.append("Una esquina está pegada al borde de la foto: el tablero puede estar cortado.")
    return advertencias


def guardar_calibracion(
    puntos: dict[str, tuple[float, float]], imagen: np.ndarray, fuente: str, advertencias: list[str]
) -> None:
    """Guarda las esquinas (las que usa el reconocimiento), la metadata de la sesión y la foto de referencia."""
    tablero.guardar_esquinas_calibradas(puntos)
    alto, ancho = imagen.shape[:2]
    metadata = {
        "esquinas": {nombre: [float(x), float(y)] for nombre, (x, y) in puntos.items()},
        "resolucion": [int(ancho), int(alto)],
        "fuente": fuente,
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "advertencias": advertencias,
    }
    ruta_metadata().write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    exito, buffer = cv2.imencode(".jpg", imagen)
    if not exito:
        raise ValueError("No se pudo codificar la foto de referencia")
    ruta_referencia().write_bytes(buffer.tobytes())


def _leer_metadata(esquinas: dict[str, list[float]]) -> dict | None:
    """Metadata de la calibración actual, o `None` si falta o pertenece a otras esquinas (p. ej. guardadas por la ruta vieja)."""
    try:
        metadata = json.loads(ruta_metadata().read_text(encoding="utf-8"))
        if metadata["esquinas"] != esquinas:
            return None
        ancho, alto = metadata["resolucion"]
        return {**metadata, "resolucion": [int(ancho), int(alto)]}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _esquinas_guardadas() -> dict[str, list[float]] | None:
    try:
        datos = json.loads(tablero.ARCHIVO_ESQUINAS.read_text(encoding="utf-8"))
        return {nombre: [float(datos[nombre][0]), float(datos[nombre][1])] for nombre in tablero.ORDEN_DE_CLICS}
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return None


def estado(resolucion_actual: tuple[int, int] | None, fuente_actual: str) -> dict:
    """Estado de la calibración: si existe y si sigue vigente para la cámara tal como está ahora.

    Args:
        resolucion_actual: `(ancho, alto)` que entrega la cámara ahora, o `None` si no se pudo capturar.
        fuente_actual: la fuente de cámara configurada (`CAMARA_FUENTE`).

    Returns:
        `{calibrada, vigente, motivo_no_vigente, esquinas, fecha, resolucion, fuente, advertencias}`. `vigente` es `None` cuando
        no se puede verificar (cámara sin imagen).
    """
    esquinas = _esquinas_guardadas()
    if esquinas is None:
        return {
            "calibrada": False, "vigente": False, "motivo_no_vigente": "Todavía no se calibró el tablero.",
            "esquinas": None, "fecha": None, "resolucion": None, "fuente": None, "advertencias": [],
        }
    metadata = _leer_metadata(esquinas)
    base = {"calibrada": True, "esquinas": esquinas}
    if metadata is None:
        return {
            **base, "vigente": False, "fecha": None, "resolucion": None, "fuente": None, "advertencias": [],
            "motivo_no_vigente": "La calibración no tiene datos de la sesión (se guardó con una versión anterior): volvé a calibrar.",
        }
    datos = {
        **base, "fecha": metadata["fecha"], "resolucion": metadata["resolucion"], "fuente": metadata["fuente"],
        "advertencias": metadata.get("advertencias", []),
    }
    if metadata["fuente"] != fuente_actual:
        motivo = f"Se calibró con la cámara «{metadata['fuente']}» y ahora se usa «{fuente_actual}»: volvé a calibrar."
        return {**datos, "vigente": False, "motivo_no_vigente": motivo}
    if resolucion_actual is None:
        return {**datos, "vigente": None, "motivo_no_vigente": "No se pudo verificar: la cámara no entrega imagen."}
    if list(resolucion_actual) != metadata["resolucion"]:
        calibrada_con = "×".join(str(n) for n in metadata["resolucion"])
        ahora = "×".join(str(n) for n in resolucion_actual)
        motivo = f"La cámara ahora entrega {ahora} y se calibró con {calibrada_con}: volvé a calibrar."
        return {**datos, "vigente": False, "motivo_no_vigente": motivo}
    return {**datos, "vigente": True, "motivo_no_vigente": None}


def comprobar_movimiento(actual: np.ndarray) -> dict:
    """Compara una foto nueva con la de referencia de la calibración para avisar si la cámara (o el tablero) se movió.

    Empareja puntos de interés (ORB) entre las dos fotos, estima el desplazamiento global con RANSAC y mide cuánto se corrieron
    las cuatro esquinas calibradas. Ignora las piezas que cambiaron de lugar porque RANSAC se queda con lo que no se movió.

    Returns:
        `{movida, desplazamiento_px, coincidencias, mensaje}`. `movida` es `None` si no se pudo comparar (sin calibración o con
        referencia, pocas coincidencias por luz distinta o manos en la foto).
    """
    esquinas = _esquinas_guardadas()
    referencia = cv2.imread(str(ruta_referencia())) if ruta_referencia().exists() else None
    if esquinas is None or referencia is None or _leer_metadata(esquinas) is None:
        return {"movida": None, "desplazamiento_px": None, "coincidencias": 0, "mensaje": "No hay una calibración con foto de referencia para comparar."}
    if actual.shape[:2] != referencia.shape[:2]:
        return {
            "movida": True, "desplazamiento_px": None, "coincidencias": 0,
            "mensaje": "La foto tiene otra resolución que la de la calibración: volvé a calibrar.",
        }
    orb = cv2.ORB_create(nfeatures=1500)
    puntos_ref, descriptores_ref = orb.detectAndCompute(cv2.cvtColor(referencia, cv2.COLOR_BGR2GRAY), None)
    puntos_act, descriptores_act = orb.detectAndCompute(cv2.cvtColor(actual, cv2.COLOR_BGR2GRAY), None)
    sin_comparar = {"movida": None, "desplazamiento_px": None, "coincidencias": 0}
    if descriptores_ref is None or descriptores_act is None or len(puntos_ref) < MINIMO_COINCIDENCIAS or len(puntos_act) < MINIMO_COINCIDENCIAS:
        return {**sin_comparar, "mensaje": "La imagen tiene muy pocos detalles para compararla con la referencia."}
    emparejador = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    coincidencias = sorted(emparejador.match(descriptores_ref, descriptores_act), key=lambda m: m.distance)[:300]
    if len(coincidencias) < MINIMO_COINCIDENCIAS:
        return {**sin_comparar, "mensaje": "Casi no hay coincidencias con la foto de referencia: ¿cambió mucho la luz o hay algo tapando el tablero?"}
    origen = np.float32([puntos_ref[m.queryIdx].pt for m in coincidencias])
    destino = np.float32([puntos_act[m.trainIdx].pt for m in coincidencias])
    matriz, aceptadas = cv2.estimateAffinePartial2D(origen, destino, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    aceptadas_n = int(aceptadas.sum()) if aceptadas is not None else 0
    if matriz is None or aceptadas_n < MINIMO_COINCIDENCIAS:
        return {**sin_comparar, "coincidencias": aceptadas_n, "mensaje": "No se pudo estimar el movimiento: probá de nuevo con el tablero despejado."}
    esquinas_ref = np.float32([esquinas[nombre] for nombre in tablero.ORDEN_DE_CLICS]).reshape(-1, 1, 2)
    esquinas_nuevas = cv2.transform(esquinas_ref, matriz)
    desplazamiento = float(np.linalg.norm((esquinas_nuevas - esquinas_ref).reshape(-1, 2), axis=1).max())
    movida = desplazamiento > UMBRAL_DESPLAZAMIENTO_PX
    mensaje = (
        f"La cámara se movió unos {desplazamiento:.0f} px respecto de la calibración: volvé a calibrar antes de jugar con el robot."
        if movida
        else "La cámara sigue en su lugar: la calibración es válida."
    )
    return {"movida": movida, "desplazamiento_px": round(desplazamiento, 1), "coincidencias": aceptadas_n, "mensaje": mensaje}


def previsualizar(imagen: np.ndarray, puntos: dict[str, tuple[float, float]]) -> np.ndarray:
    """Tablero enderezado con la grilla 8x8 y el marco con sus letras alrededor, como lo vería el reconocimiento con esas esquinas."""
    esquinas = np.array([puntos[nombre] for nombre in tablero.ORDEN_DE_ENDEREZADO], dtype=np.float32)
    return tablero.imagen_control_ampliada(imagen, esquinas)
