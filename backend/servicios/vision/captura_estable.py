"""Lee la ocupación del tablero con VOTACIÓN entre varios cuadros de la cámara en vivo.

Un solo cuadro puede salir con la mano encima, borroso o con una sombra; votando entre varios (y descartando los que no coinciden con
la mayoría) el resultado es estable. Devuelve `{casilla: vacia|blanca|negra}`.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from backend.servicios.vision import ocupacion
from backend.servicios.vision.fusion import fusionar_probabilidades
from backend.servicios.vision.camara import camaras_configuradas, capturar_foto_tablero, flujo_de_frames
from backend.servicios.vision.jugada_probable import Lectura
from backend.servicios.vision.reconocimiento import esquinas_y_margen
from backend.servicios.vision.tablero import dividir_en_casillas, enderezar_tablero

CUADROS = 7
ACUERDO_MINIMO = 0.6
"""Fracción de cuadros que deben coincidir en una casilla para darla por vista; por debajo, la lectura se considera inestable."""


def ocupacion_de_imagen(imagen: np.ndarray, camara: str = "principal", esquinas: np.ndarray | None = None) -> np.ndarray:
    """Probabilidades `(64, 3)` de una foto de `camara`, en el orden de `casillas` (a8, b8 … h1). `esquinas` fuerza esas (ver `recortes_de_imagen`)."""
    esquinas, margen = (np.asarray(esquinas, dtype=np.float32), 0.0) if esquinas is not None else esquinas_y_margen(imagen, camara)
    if not margen and ocupacion.modo_recorte() == "base":
        from backend.servicios.vision import geometria3d

        alto, ancho = imagen.shape[:2]
        casillas = geometria3d.recortes_base(imagen, esquinas[::-1], geometria3d.cargar_lente(camara, ancho, alto))  # a8,h8,h1,a1 -> a1,h1,h8,a8
    else:
        casillas = dividir_en_casillas(enderezar_tablero(imagen, esquinas), margen)
    return ocupacion.clasificar_ocupacion(list(casillas.values()))


def camaras_calibradas() -> list[str]:
    """Las cámaras con las que se reconoce: la principal y, si está configurada y calibrada, la secundaria."""
    from backend.servicios.vision.tablero import archivo_esquinas

    return [c for c in camaras_configuradas() if c == "principal" or archivo_esquinas(c).exists()]


def ocupacion_fusionada(frame_principal: np.ndarray) -> np.ndarray:
    """Ocupación `(64, 3)` fusionando (producto de las probabilidades) la de la cámara principal (`frame_principal`) con la de la secundaria, si hay.

    La secundaria se lee de su captura continua (el último cuadro); si falla o no detecta el tablero, se sigue solo con la principal.
    """
    lecturas = [ocupacion_de_imagen(frame_principal, "principal")]
    for camara in camaras_calibradas():
        if camara == "principal":
            continue
        try:
            lecturas.append(ocupacion_de_imagen(capturar_foto_tablero(camara=camara), camara))
        except (RuntimeError, ValueError):
            continue
    return fusionar_probabilidades(lecturas)


def ocupacion_de_fotos(fotos: dict[str, np.ndarray]) -> np.ndarray:
    """Ocupación `(64, 3)` fusionando (producto de las probabilidades) la de cada cámara de `fotos` (`{camara: imagen}`).

    Una cámara cuyo tablero no se detecta se omite; si ninguna sirve, lanza `ValueError`.
    """
    lecturas = []
    for camara, imagen in fotos.items():
        try:
            lecturas.append(ocupacion_de_imagen(imagen, camara))
        except ValueError:
            continue
    if not lecturas:
        raise ValueError("No se detectó el tablero en ninguna cámara")
    return fusionar_probabilidades(lecturas)


def camaras_a_usar(camaras: list[str] | None = None) -> list[str]:
    """Las cámaras con las que leer: todas las calibradas (`camaras=None`) o solo las pedidas que estén calibradas, en el orden dado.

    Raises:
        ValueError: ninguna de las pedidas está calibrada.
    """
    disponibles = camaras_calibradas()
    if camaras is None:
        return disponibles
    elegidas = [c for c in camaras if c in disponibles]
    if not elegidas:
        raise ValueError(f"Ninguna de las cámaras pedidas ({', '.join(camaras) or 'ninguna'}) está calibrada")
    return elegidas


NOMBRES = [f"{c}{f}" for f in range(8, 0, -1) for c in "abcdefgh"]


def votar(lecturas: list[np.ndarray]) -> tuple[dict[str, str], float]:
    """Mayoría por casilla entre lecturas `(64, 3)`. Devuelve `(mapa, acuerdo_minimo)`; el acuerdo es el de la casilla más dudosa."""
    etiquetas = np.argmax(np.stack(lecturas), axis=2)  # (cuadros, 64)
    mapa, peor = {}, 1.0
    for i, nombre in enumerate(NOMBRES):
        ganador, votos = Counter(etiquetas[:, i].tolist()).most_common(1)[0]
        mapa[nombre] = ocupacion.CLASES_OCUPACION[ganador]
        peor = min(peor, votos / len(lecturas))
    return mapa, peor


def leer_ocupacion_estable(cuadros: int = CUADROS) -> tuple[dict[str, str], float]:
    """Toma `cuadros` cuadros seguidos del video en vivo y devuelve la ocupación por mayoría y el acuerdo (0-1).

    Raises:
        RuntimeError: la cámara no está disponible o dejó de entregar imágenes.
        ValueError: no se detectó el tablero.
    """
    lecturas = []
    for frame in flujo_de_frames():
        lecturas.append(ocupacion_fusionada(frame))
        if len(lecturas) >= cuadros:
            break
    if not lecturas:
        raise RuntimeError("La cámara no entrega imágenes")
    return votar(lecturas)


PESO_PIEZAS = 0.5
"""Cuánto pesa el modelo de piezas (13 clases, menos preciso) frente al de ocupación (vacía/blanca/negra) al decidir una jugada."""


def _media_geometrica(matrices: list[np.ndarray]) -> np.ndarray:
    """Promedio de los logaritmos de varias lecturas `(64, clases)` (un cuadro suelto malo no decide), renormalizado por fila."""
    logaritmo = np.mean([np.log(np.asarray(m, dtype=np.float64) + 1e-3) for m in matrices], axis=0)
    resultado = np.exp(logaritmo)
    return resultado / resultado.sum(axis=1, keepdims=True)


def leer_lecturas_estables(cuadros: int = CUADROS, camaras: list[str] | None = None) -> list[Lectura]:
    """Lo que ven las cámaras, promediado entre `cuadros` cuadros del video en vivo, listo para `jugada_probable.detectar_jugada_probable`.

    Devuelve la lectura de ocupación (siempre) y la de las 13 clases de pieza si hay un modelo entrenado. `camaras` elige con cuáles leer
    (`["principal"]`, `["secundaria"]` o las dos); `None` usa todas las calibradas. Con más de una, cada lectura ya viene fusionada entre ellas.

    Raises:
        FileNotFoundError: no hay modelo de ocupación entrenado (el que da la base de la jugada).
        RuntimeError: la cámara no está disponible o dejó de entregar imágenes. ValueError: no se detectó el tablero, o las cámaras pedidas no están calibradas.
    """
    from backend.servicios.vision import verificacion

    elegidas = camaras_a_usar(camaras)
    base = elegidas[0]
    ocupaciones, piezas_leidas, clases_piezas = [], [], None
    for frame in flujo_de_frames(camara=base):
        fotos = {base: frame}
        for camara in elegidas[1:]:
            try:
                fotos[camara] = capturar_foto_tablero(camara=camara)
            except RuntimeError:
                continue  # la otra cámara falló: se sigue con las que respondan
        ocupaciones.append(ocupacion_de_fotos(fotos))
        try:
            probs, _, clases_piezas = verificacion.probabilidades_de_piezas(fotos)
            piezas_leidas.append(probs)
        except (FileNotFoundError, ValueError):
            pass  # sin modelo de piezas (o sin tablero detectado en este cuadro): se decide solo con la ocupación
        if len(ocupaciones) >= cuadros:
            break
    if not ocupaciones:
        raise RuntimeError("La cámara no entrega imágenes")
    lecturas = [Lectura(_media_geometrica(ocupaciones), list(ocupacion.CLASES_OCUPACION), 1.0)]
    if piezas_leidas:
        lecturas.append(Lectura(_media_geometrica(piezas_leidas), list(clases_piezas), PESO_PIEZAS))
    return lecturas


def detectar_casilla_de_pieza(probabilidades: np.ndarray, color: str) -> tuple[str | None, float, str]:
    """En qué casilla está una pieza sola de `color` ("blanca" o "negra"), según las probabilidades `(64, 3)` de ocupación.

    Se queda con la casilla donde es más probable ese color. Devuelve `(casilla, confianza, estado)`: `estado` es `"ok"`,
    `"ninguna"` (no se ve pieza de ese color) o `"ambigua"` (hay otra casilla casi igual de probable: por ejemplo, la pieza se
    inclina sobre la vecina o hay más de una pieza), y en esos dos casos `casilla` es `None`.
    """
    columna = ocupacion.CLASES_OCUPACION.index(color)
    puntajes = probabilidades[:, columna]
    orden = np.argsort(puntajes)[::-1]
    mejor, segunda = float(puntajes[orden[0]]), float(puntajes[orden[1]])
    if mejor < UMBRAL_PIEZA:
        return None, mejor, "ninguna"
    if segunda > UMBRAL_AMBIGUA and segunda > FRACCION_AMBIGUA * mejor:  # una pieza inclinada puede 'tocar' la vecina con menos fuerza
        return None, mejor, "ambigua"
    return NOMBRES[int(orden[0])], mejor, "ok"


UMBRAL_PIEZA = 0.7
UMBRAL_AMBIGUA = 0.5
FRACCION_AMBIGUA = 0.75
