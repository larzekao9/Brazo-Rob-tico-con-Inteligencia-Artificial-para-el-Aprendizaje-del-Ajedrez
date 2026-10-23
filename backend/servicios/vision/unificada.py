"""Calibración unificada de las dos cámaras: comprueba que describen el MISMO tablero y con la misma orientación.

Cada cámara se calibra por separado marcando a1, h1, h8 y a8. Si las dos se marcaron igual, al enderezar la foto de cada una con sus esquinas
el tablero queda en el mismo lugar y con la misma orientación: la casilla e4 es el mismo cuadro en las dos. Aquí se comprueba comparando
las dos imágenes enderezadas (con el marco de madera y sus letras alrededor, que rompen la simetría del damero):

- **Orientación:** se prueba la imagen de la secundaria girada 0/90/180/270° y espejada. Las líneas de un damero son iguales en las 8 versiones,
  así que no sirven para decidir (con la luz y la madera distintas de cada cámara daban "espejada" a dos calibraciones correctas). Lo que sí
  distingue es el COLOR de las casillas: espejar o girar 90° cambia las claras por las oscuras, así que esas versiones se descartan por el
  signo de la correlación de gris del área de juego. Entre las que conservan los colores (sin giro, 180° y las dos diagonales) decide el
  marco con sus letras impresas, que es lo único que rompe esa simetría.
- **Alineación por esquina:** en cada imagen enderezada se ubican al subpíxel las 49 esquinas internas del damero (las que no tapa una
  pieza) y se mide cuánto se aleja cada una de donde debería estar y de la misma esquina en la otra cámara. Un solo corrimiento global (la
  correlación de fase, que se sigue calculando) promedia todo y esconde que el error se junta en los bordes y las esquinas del tablero.
- **Esquinas sugeridas:** con las esquinas internas medidas se ajusta la grilla completa y se recalculan a1, h1, h8 y a8 al subpíxel: más
  preciso que marcar 4 puntos a mano, porque usa hasta 49 puntos en vez de 4.

Un tablero girado 180° respecto del impreso se ve igual que el correcto, y si las DOS cámaras están giradas igual coinciden entre sí: eso no
lo detecta esta verificación sino `validacion_orientacion`, con el color de las piezas al capturar.
"""
from __future__ import annotations

import base64

import cv2
import numpy as np

from backend.servicios.vision.tablero import ORDEN_DE_ENDEREZADO, archivo_esquinas, cargar_esquinas_calibradas, enderezar_con_marco

TAMANO = 800
MARGEN_RELATIVO = 0.12
CASILLA_PX = TAMANO * (1 - 2 * MARGEN_RELATIVO) / 8
"""Lado de una casilla en la imagen enderezada (76 px)."""
ERROR_BIEN = 0.15
ERROR_REGULAR = 0.40
"""Error de alineación, en casillas: hasta ERROR_BIEN la calibración es buena, hasta ERROR_REGULAR se puede mejorar, y más es mala."""
MEJORA_MINIMA = 0.02
"""Cuánto más se tiene que parecer el MARCO de otra orientación (con los mismos colores de casilla) que el de la original para decir que la
cámara está girada. Con fotos reales la orientación correcta le gana a las demás por 0,03 o más."""
COLORES_INVERTIDOS = -0.5
"""Correlación de gris del área de juego por debajo de la cual las casillas claras de una cámara caen sobre las oscuras de la otra (espejada o
girada 90°: con fotos reales ronda −0,85). Entre esto y 0 lo que hay es un corrimiento grande de las esquinas (media casilla o más), no un giro."""
MINIMO_ESQUINAS = 20
"""Esquinas internas (de 49) que hacen falta para medir por esquina o sugerir esquinas; con menos (muchas piezas encima) se usa el corrimiento global."""
CONTRASTE_MINIMO = 25.0
"""Diferencia de gris entre los cuadrantes claros y oscuros alrededor de una esquina para creer que es una esquina del damero y no una pieza."""
CORRIMIENTO_MAXIMO = 0.40
"""Hasta cuánto (en casillas) se busca cada esquina interna lejos de donde la pone la calibración."""

_TRANSFORMACIONES = [
    ("sin giro", 0, False), ("girada 90°", 90, False), ("girada 180°", 180, False), ("girada 270°", 270, False),
    ("espejada", 0, True), ("espejada y girada 90°", 90, True), ("espejada y girada 180°", 180, True), ("espejada y girada 270°", 270, True),
]
_GIROS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
_CRITERIO_SUBPIXEL = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.01)


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


def _gris_del_juego(imagen_bgr: np.ndarray) -> np.ndarray:
    """Área de juego en gris, muy suavizada y normalizada: queda el patrón de casillas claras y oscuras, sin la textura de la madera."""
    borde = int(round(TAMANO * MARGEN_RELATIVO))
    gris = cv2.GaussianBlur(cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 8)[borde:-borde, borde:-borde]
    return (gris - gris.mean()) / (gris.std() + 1e-6)


def _bordes_del_marco(imagen_bgr: np.ndarray) -> np.ndarray:
    """Bordes solo del marco (letras y números impresos), con el área de juego en cero."""
    bordes = _bordes(imagen_bgr)
    interior = int(round(TAMANO * MARGEN_RELATIVO)) + 8
    bordes[interior:-interior, interior:-interior] = 0
    return bordes


def _orientacion(a: np.ndarray, b: np.ndarray) -> tuple[str, bool, dict, dict]:
    """`(mejor, desorientada, colores, marco)`: qué versión de `b` coincide con `a` y si es distinta de la original (ver docstring del módulo).

    `colores` es la correlación de gris del área de juego (positiva: mismos colores de casilla) y `marco` la de los bordes del marco.
    """
    gris_a, marco_a = _gris_del_juego(a), _bordes_del_marco(a)
    colores, marco = {}, {}
    for nombre, giro, espejo in _TRANSFORMACIONES:
        version = _aplicar(b, giro, espejo)
        colores[nombre] = float((gris_a * _gris_del_juego(version)).mean())
        marco[nombre] = _correlacion(marco_a, _bordes_del_marco(version))
    candidatas = [nombre for nombre in colores if colores[nombre] > 0] or list(colores)
    mejor = max(candidatas, key=marco.get)
    if colores["sin giro"] <= COLORES_INVERTIDOS:  # las casillas claras de una caen sobre las oscuras de la otra: girada o espejada
        return mejor, True, colores, marco
    if colores["sin giro"] <= 0:  # a medio camino: las esquinas están muy corridas, no giradas (lo informa la alineación)
        return "sin giro", False, colores, marco
    desorientada = mejor != "sin giro" and marco[mejor] > marco["sin giro"] + MEJORA_MINIMA
    return (mejor if desorientada else "sin giro"), desorientada, colores, marco


# --- esquinas internas -----------------------------------------------------------------------------------------------------
def _cuadricula_interna() -> np.ndarray:
    """`(49, 2)` índices `(columna, fila)` de 1 a 7 de cada esquina interna, fila por fila desde el lado de la fila 8."""
    return np.array([(i, j) for j in range(1, 8) for i in range(1, 8)], dtype=np.float64)


def _posiciones_ideales() -> np.ndarray:
    """Dónde cae cada esquina interna en la imagen enderezada (`enderezar_con_marco`) si la calibración es perfecta."""
    return (TAMANO * MARGEN_RELATIVO + _cuadricula_interna() * CASILLA_PX).astype(np.float32)


def nombre_esquina(indice: int) -> str:
    """Nombre legible de la esquina interna `indice` (0-48): las dos casillas en diagonal que la tocan, p. ej. `d4/e5`."""
    columna, fila = (int(v) for v in _cuadricula_interna()[indice])
    return f"{'abcdefgh'[columna - 1]}{8 - fila}/{'abcdefgh'[columna]}{9 - fila}"


def _contraste_de_silla(gris: np.ndarray, x: float, y: float) -> float:
    """Cuánto se parece el entorno de `(x, y)` a una esquina del damero: cuadrantes en diagonal iguales y vecinos opuestos."""
    lado, hueco = int(CASILLA_PX * 0.3), 4
    xi, yi = int(round(x)), int(round(y))
    if xi - hueco - lado < 0 or yi - hueco - lado < 0 or xi + hueco + lado > gris.shape[1] or yi + hueco + lado > gris.shape[0]:
        return 0.0
    arriba_izq = gris[yi - hueco - lado : yi - hueco, xi - hueco - lado : xi - hueco].mean()
    arriba_der = gris[yi - hueco - lado : yi - hueco, xi + hueco : xi + hueco + lado].mean()
    abajo_izq = gris[yi + hueco : yi + hueco + lado, xi - hueco - lado : xi - hueco].mean()
    abajo_der = gris[yi + hueco : yi + hueco + lado, xi + hueco : xi + hueco + lado].mean()
    return float(abs((arriba_izq + abajo_der) - (arriba_der + abajo_izq)) / 2)


def medir_esquinas_internas(enderezada: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Ubica al subpíxel las 49 esquinas internas del damero en una imagen de `enderezar_con_marco`.

    Cada esquina se busca cerca de donde la pone la calibración. Se descarta (pieza encima, reflejo) si dos búsquedas con ventanas
    distintas no coinciden, si queda a más de `CORRIMIENTO_MAXIMO` casillas o si su entorno no tiene contraste de esquina de damero.

    Returns:
        `(posiciones (49, 2), validas (49,) bool)`.
    """
    gris = cv2.cvtColor(enderezada, cv2.COLOR_BGR2GRAY)
    ideales = _posiciones_ideales().reshape(-1, 1, 2)
    gruesa = int(CASILLA_PX * 0.35)  # primero una búsqueda amplia (una esquina mal marcada puede estar a un tercio de casilla), después fina
    aproximadas = cv2.cornerSubPix(gris, ideales.copy(), (gruesa, gruesa), (-1, -1), _CRITERIO_SUBPIXEL)
    chica = cv2.cornerSubPix(gris, aproximadas.copy(), (9, 9), (-1, -1), _CRITERIO_SUBPIXEL).reshape(-1, 2)
    grande = cv2.cornerSubPix(gris, aproximadas.copy(), (15, 15), (-1, -1), _CRITERIO_SUBPIXEL).reshape(-1, 2)
    ideales = ideales.reshape(-1, 2)
    validas = (
        (np.linalg.norm(chica - grande, axis=1) < 1.5)
        & (np.linalg.norm(grande - ideales, axis=1) < CORRIMIENTO_MAXIMO * CASILLA_PX)
        & np.array([_contraste_de_silla(gris, x, y) >= CONTRASTE_MINIMO for x, y in grande])
    )
    return grande, validas


def _resumen_errores(errores_px: np.ndarray, validas: np.ndarray) -> dict:
    """Máximo, medio y la peor esquina (en casillas) de los errores de las esquinas válidas."""
    medidas = errores_px[validas]
    peor = int(np.flatnonzero(validas)[np.argmax(medidas)])
    return {
        "esquinas_medidas": int(validas.sum()),
        "error_max_casillas": round(float(medidas.max() / CASILLA_PX), 2),
        "error_medio_casillas": round(float(medidas.mean() / CASILLA_PX), 2),
        "peor_esquina": nombre_esquina(peor),
    }


def sugerir_esquinas(foto: np.ndarray, esquinas: np.ndarray) -> dict | None:
    """a1, h1, h8, a8 recalculadas ajustando la grilla a las esquinas internas que se ven en `foto`.

    `esquinas` son las calibradas (orden de `enderezar_tablero`). Se enderezan con ellas, se miden las esquinas internas, se llevan de vuelta a
    la foto original y se ajusta una homografía (con RANSAC, para que una esquina mal medida no la arrastre) de la grilla ideal a esos puntos.

    Returns:
        `{esquinas: {a1: [x, y], ...}, esquinas_enderezado (4, 2), error_actual_casillas, error_sugeridas_casillas, esquinas_medidas}`, o `None`
        si se ven menos de `MINIMO_ESQUINAS` esquinas internas (piezas encima).
    """
    esquinas = np.asarray(esquinas, dtype=np.float32)
    enderezada = enderezar_con_marco(foto, esquinas, MARGEN_RELATIVO, TAMANO)
    posiciones, validas = medir_esquinas_internas(enderezada)
    if validas.sum() < MINIMO_ESQUINAS:
        return None
    borde = TAMANO * MARGEN_RELATIVO
    destino = np.array([[borde, borde], [TAMANO - borde, borde], [TAMANO - borde, TAMANO - borde], [borde, TAMANO - borde]], dtype=np.float32)
    a_original = np.linalg.inv(cv2.getPerspectiveTransform(esquinas, destino))
    en_la_foto = cv2.perspectiveTransform(posiciones[validas].reshape(-1, 1, 2).astype(np.float64), a_original).reshape(-1, 2)
    matriz, _ = cv2.findHomography(_cuadricula_interna()[validas], en_la_foto, cv2.RANSAC, 2.0)
    if matriz is None:
        return None
    exteriores = np.array([[0, 0], [8, 0], [8, 8], [0, 8]], dtype=np.float64)  # a8, h8, h1, a1 en casillas
    nuevas = cv2.perspectiveTransform(exteriores.reshape(-1, 1, 2), matriz).reshape(4, 2).astype(np.float32)
    error_actual = _resumen_errores(np.linalg.norm(posiciones - _posiciones_ideales(), axis=1), validas)["error_max_casillas"]
    nuevas_pos, nuevas_validas = medir_esquinas_internas(enderezar_con_marco(foto, nuevas, MARGEN_RELATIVO, TAMANO))
    error_nuevo = (
        _resumen_errores(np.linalg.norm(nuevas_pos - _posiciones_ideales(), axis=1), nuevas_validas)["error_max_casillas"]
        if nuevas_validas.sum() >= MINIMO_ESQUINAS else None
    )
    return {
        "esquinas": {nombre: [round(float(x), 1), round(float(y), 1)] for nombre, (x, y) in zip(ORDEN_DE_ENDEREZADO, nuevas)},
        "esquinas_enderezado": nuevas,
        "error_actual_casillas": error_actual,
        "error_sugeridas_casillas": error_nuevo,
        "esquinas_medidas": int(validas.sum()),
    }


# --- imagen del informe ----------------------------------------------------------------------------------------------------
def _rotulo(imagen: np.ndarray, texto: str) -> np.ndarray:
    cv2.putText(imagen, texto, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(imagen, texto, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    return imagen


def _mapa_de_esquinas(fondo: np.ndarray, a: np.ndarray, b: np.ndarray, comunes: np.ndarray) -> np.ndarray:
    """La imagen principal atenuada con cada esquina interna medida en las dos cámaras: un círculo verde/ámbar/rojo según el error y una
    flecha (exagerada ×3) hacia donde la ve la secundaria. Las esquinas que no se pudieron medir (pieza encima) quedan en gris."""
    mapa = cv2.addWeighted(fondo, 0.45, np.zeros_like(fondo), 0.55, 0)
    for indice, (pa, pb) in enumerate(zip(a, b)):
        centro = tuple(int(round(v)) for v in _posiciones_ideales()[indice])
        if not comunes[indice]:
            cv2.circle(mapa, centro, 5, (150, 150, 150), 1, cv2.LINE_AA)
            continue
        error = float(np.linalg.norm(pb - pa) / CASILLA_PX)
        color = (0, 200, 0) if error <= ERROR_BIEN else (0, 190, 255) if error <= ERROR_REGULAR else (0, 0, 255)
        inicio = tuple(int(round(v)) for v in pa)
        fin = tuple(int(round(v)) for v in pa + 3 * (pb - pa))
        cv2.arrowedLine(mapa, inicio, fin, color, 2, cv2.LINE_AA, tipLength=0.3)
        cv2.circle(mapa, inicio, 7, color, -1, cv2.LINE_AA)
    return mapa


def _panel(principal: np.ndarray, secundaria: np.ndarray, cuarto: np.ndarray, titulo_cuarto: str, lado: int = 400) -> np.ndarray:
    """Cuadrícula 2×2: principal, secundaria, las dos superpuestas (mitad y mitad) y el mapa de esquinas (o de diferencia)."""
    mezcla = cv2.addWeighted(principal, 0.5, secundaria, 0.5, 0)
    paso = TAMANO * MARGEN_RELATIVO
    for i in range(9):  # grilla 8x8 de referencia sobre la mezcla
        x = int(round(paso + i * CASILLA_PX))
        cv2.line(mezcla, (x, int(paso)), (x, int(TAMANO - paso)), (255, 255, 255), 1)
        cv2.line(mezcla, (int(paso), x), (int(TAMANO - paso), x), (255, 255, 255), 1)
    paneles = [
        _rotulo(cv2.resize(imagen, (lado, lado)), texto)
        for imagen, texto in ((principal, "principal"), (secundaria, "secundaria"), (mezcla, "superpuestas"), (cuarto, titulo_cuarto))
    ]
    return np.vstack([np.hstack(paneles[:2]), np.hstack(paneles[2:])])


# --- verificación ----------------------------------------------------------------------------------------------------------
def _informe_camara(foto: np.ndarray, esquinas: np.ndarray, posiciones: np.ndarray, validas: np.ndarray) -> dict:
    """Cuánto se aleja cada cámara de su propia grilla ideal y qué esquinas se le sugieren."""
    if validas.sum() < MINIMO_ESQUINAS:
        return {"esquinas_medidas": int(validas.sum()), "error_max_casillas": None, "error_medio_casillas": None, "peor_esquina": None, "sugeridas": None}
    resumen = _resumen_errores(np.linalg.norm(posiciones - _posiciones_ideales(), axis=1), validas)
    sugerencia = sugerir_esquinas(foto, esquinas)
    resumen["sugeridas"] = (
        {"esquinas": sugerencia["esquinas"], "error_casillas": sugerencia["error_sugeridas_casillas"]} if sugerencia else None
    )
    return resumen


def comparar(foto_principal: np.ndarray, foto_secundaria: np.ndarray, esquinas_principal: np.ndarray, esquinas_secundaria: np.ndarray) -> dict:
    """Compara las dos fotos enderezadas con sus esquinas (orden de `enderezar_tablero`) y devuelve el informe y la imagen.

    Returns:
        `{nivel, ok, mensaje, error_px, error_casillas, orientacion, por_esquina, corrimiento_global, camaras, imagen}`. `error_*` es el de la
        peor esquina interna entre las dos cámaras (o el corrimiento global si se ven pocas esquinas); `camaras` dice, para cada una, cuánto se
        aleja de su propia grilla y las esquinas sugeridas para corregirlo.
    """
    a = enderezar_con_marco(foto_principal, esquinas_principal, MARGEN_RELATIVO, TAMANO)
    b = enderezar_con_marco(foto_secundaria, esquinas_secundaria, MARGEN_RELATIVO, TAMANO)
    bordes_a = _bordes(a)
    mejor, desorientada, colores, puntajes = _orientacion(a, b)

    # Corrimiento global (con la secundaria ya en su mejor orientación, para medirlo aunque esté girada).
    giro, espejo = next((g, e) for nombre, g, e in _TRANSFORMACIONES if nombre == mejor)
    b_orientada = _aplicar(b, giro, espejo) if desorientada else b
    ventana = cv2.createHanningWindow((TAMANO, TAMANO), cv2.CV_32F)
    (dx, dy), _ = cv2.phaseCorrelate(bordes_a, _bordes(b_orientada), ventana)
    global_px = float(np.hypot(dx, dy))

    pos_a, val_a = medir_esquinas_internas(a)
    pos_b, val_b = medir_esquinas_internas(b)
    comunes = val_a & val_b
    camaras = {
        "principal": _informe_camara(foto_principal, esquinas_principal, pos_a, val_a),
        "secundaria": _informe_camara(foto_secundaria, esquinas_secundaria, pos_b, val_b),
    }
    por_esquina = None
    if not desorientada and comunes.sum() >= MINIMO_ESQUINAS:
        por_esquina = _resumen_errores(np.linalg.norm(pos_a - pos_b, axis=1), comunes)
        error_casillas = por_esquina["error_max_casillas"]
        imagen = _panel(a, b, _mapa_de_esquinas(a, pos_a, pos_b, comunes), "esquinas (flecha x3)")
    else:
        error_casillas = global_px / CASILLA_PX
        imagen = _panel(a, b, cv2.applyColorMap(
            cv2.normalize(np.abs(bordes_a - _bordes(b)), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8), cv2.COLORMAP_JET
        ), "diferencia")
    error_px = error_casillas * CASILLA_PX

    if desorientada:
        nivel = "orientacion"
        mensaje = (
            f"La cámara secundaria parece estar {mejor} respecto de la principal. Giró la imagen de la secundaria (Elegir cámaras → "
            "Girar la secundaria) o recalibrala marcando las esquinas en el mismo orden: a1, h1, h8 y a8 según las letras impresas."
        )
    else:
        nivel = "bien" if error_casillas <= ERROR_BIEN else "regular" if error_casillas <= ERROR_REGULAR else "mal"
        mensaje = _mensaje(nivel, error_casillas, por_esquina, camaras)
    exito, buffer = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not exito:
        raise RuntimeError("No se pudo codificar la imagen de la verificación")
    return {
        "nivel": nivel,
        "ok": nivel in ("bien", "regular"),
        "mensaje": mensaje,
        "error_px": round(error_px, 1),
        "error_casillas": round(error_casillas, 2),
        "orientacion": {
            "mejor": mejor,
            "puntajes": {nombre: round(v, 3) for nombre, v in puntajes.items()},
            "colores": {nombre: round(v, 3) for nombre, v in colores.items()},
        },
        "por_esquina": por_esquina,
        "corrimiento_global": {"error_px": round(global_px, 1), "error_casillas": round(global_px / CASILLA_PX, 2)},
        "camaras": camaras,
        "imagen": base64.b64encode(buffer.tobytes()).decode("ascii"),
    }


def _mensaje(nivel: str, error_casillas: float, por_esquina: dict | None, camaras: dict) -> str:
    """Mensaje del informe: cuánto coinciden, dónde está el peor error y qué cámara conviene corregir."""
    if por_esquina is None:
        base = f"Corrimiento global de {error_casillas:.2f} casillas. Se ven pocas esquinas del damero (¿piezas encima?): sacá las piezas para medir esquina por esquina."
        return base if nivel != "mal" else base + " Recalibrá la cámara que tenga las esquinas peor puestas."
    detalle = f"error máximo de {error_casillas:.2f} casillas en la esquina {por_esquina['peor_esquina']} (medio {por_esquina['error_medio_casillas']:.2f}, {por_esquina['esquinas_medidas']} esquinas medidas)"
    if nivel == "bien":
        return f"Las dos calibraciones coinciden: {detalle}."
    medidas = {c: d for c, d in camaras.items() if d["error_max_casillas"] is not None}
    culpable = max(medidas, key=lambda c: medidas[c]["error_max_casillas"]) if medidas else None
    consejo = ""
    if culpable:
        datos = medidas[culpable]
        consejo = (
            f" La que más se aleja de su propia grilla es la {culpable} ({datos['error_max_casillas']:.2f} casillas cerca de {datos['peor_esquina']})"
        )
        consejo += ": usá «Ajustar esquinas» en esa cámara." if datos.get("sugeridas") else ": recalibrala marcando las esquinas con más cuidado."
    return f"Las calibraciones no coinciden del todo: {detalle}.{consejo}"


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
