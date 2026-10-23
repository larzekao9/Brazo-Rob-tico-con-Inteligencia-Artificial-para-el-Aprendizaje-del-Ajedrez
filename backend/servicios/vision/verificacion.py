"""Probador de piezas: foto(s) de la cámara fija -> qué reconoce el modelo en cada casilla (sin guardar nada).

Con dos cámaras calibradas se FUSIONAN: cada una da la probabilidad de cada clase por casilla y se promedian, de modo que una vista
dudosa (pieza tapada, perspectiva) se corrige con la otra. Los nombres de casilla son los mismos en las dos porque las dos se calibran
con la convención a1/h1/h8/a8.
"""
from __future__ import annotations

import base64

import cv2
import numpy as np

from backend.servicios.vision import piezas
from backend.servicios.vision.fusion import casillas_en_desacuerdo, fusionar_probabilidades
from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.modelo_piezas import CLASE_VACIA
from backend.servicios.vision.reconocimiento import esquinas_y_margen, recortes_de_imagen
from backend.servicios.vision.tablero import dibujar_grilla_debug, enderezar_tablero, imagen_control_ampliada

_ABREVIATURA = {"pawn": "P", "knight": "N", "bishop": "B", "rook": "R", "queen": "Q", "king": "K"}


def _etiqueta_corta(clase: str) -> str:
    color, pieza = clase.split("-")
    letra = _ABREVIATURA[pieza]
    return letra if color == "white" else letra.lower()


def probabilidades_de_camara(
    imagen: np.ndarray, camara: str = "principal", ocupadas: set[str] | None = None
) -> tuple[np.ndarray, list[str], np.ndarray, float]:
    """`(probabilidades (64, clases), nombres de casilla, esquinas, margen)` de una foto de `camara`.

    Con `ocupadas` (las casillas con pieza según la cámara de arriba, ver `ocupadas_de_arriba`) el modelo solo mira esas y las demás quedan
    "vacía" con certeza: con una red preentrenada (la de Colab) clasificar las 64 casillas tarda más de un segundo por cámara en CPU.

    Raises:
        ValueError: tablero no detectado.
    """
    recortes, esquinas, margen = recortes_de_imagen(imagen, camara)
    nombres = list(recortes)
    if ocupadas is None:
        return piezas.probabilidades([recortes[n] for n in nombres]), nombres, esquinas, margen
    clases = piezas.clases_del_modelo()
    probs = np.zeros((len(nombres), len(clases)))
    probs[:, clases.index(CLASE_VACIA)] = 1.0
    filas = [i for i, nombre in enumerate(nombres) if nombre in ocupadas]
    if filas:
        probs[filas] = piezas.probabilidades([recortes[nombres[i]] for i in filas])
    return probs, nombres, esquinas, margen


def ocupadas_de_arriba(fotos: dict[str, np.ndarray]) -> set[str] | None:
    """Las casillas con pieza según la cámara menos inclinada (`referencia_vacia.ocupadas`), o `None` si ninguna tiene referencia del tablero vacío."""
    from backend.servicios.vision import referencia_vacia

    resultado = referencia_vacia.ocupadas(fotos)
    return None if resultado is None else {nombre for nombre, ocupada in zip(referencia_vacia.NOMBRES, resultado[0]) if ocupada}


def _con_ocupacion_de_arriba(probs: np.ndarray, nombres: list[str], clases: list[str], fotos: dict[str, np.ndarray] | None) -> np.ndarray:
    """`probs` con QUÉ casillas están ocupadas decidido por la cámara que mira más desde arriba (`referencia_vacia.ocupadas`).

    El modelo de piezas sabe bien qué pieza es, pero desde una cámara en diagonal ve la cabeza de una pieza alta sobre la casilla vecina. La
    diferencia con el tablero vacío en la cámara de arriba no tiene ese problema: donde no cambió nada la casilla queda vacía, y donde cambió se
    descarta "vacía" y queda la pieza más probable. Sin referencia del tablero vacío devuelve `probs` igual.
    """
    if not fotos or CLASE_VACIA not in clases:
        return probs
    from backend.servicios.vision import referencia_vacia

    resultado = referencia_vacia.ocupadas(fotos)
    if resultado is None:
        return probs
    ocupada = dict(zip(referencia_vacia.NOMBRES, resultado[0]))
    vacia = clases.index(CLASE_VACIA)
    corregidas = np.array(probs, dtype=np.float64, copy=True)
    for fila, nombre in enumerate(nombres):
        if not ocupada[nombre]:
            corregidas[fila] = 0.0
            corregidas[fila, vacia] = 1.0
            continue
        corregidas[fila, vacia] = 0.0
        total = corregidas[fila].sum()
        corregidas[fila] = corregidas[fila] / total if total > 0 else np.where(np.arange(len(clases)) == vacia, 0.0, 1.0 / (len(clases) - 1))
    return corregidas


def _casillas_de_probabilidades(
    probs: np.ndarray, nombres: list[str], clases: list[str] | None = None, fotos: dict[str, np.ndarray] | None = None
) -> list[dict]:
    """Las predicciones por casilla: la ocupación decidida por la cámara de arriba (`_con_ocupacion_de_arriba`, con las `fotos` de cada
    cámara) y sin material ni posiciones imposibles (ver `validacion_posicion.limitar_por_material`)."""
    from backend.servicios.vision.validacion_posicion import limitar_por_material

    clases = clases or piezas.clases_del_modelo()
    probs = limitar_por_material(_con_ocupacion_de_arriba(probs, nombres, clases, fotos), clases, nombres)
    casillas = []
    for nombre, top in zip(nombres, piezas.mejores_clases(probs, clases=clases)):
        clase, confianza = top[0]
        casillas.append(
            {"casilla": nombre, "clase": clase, "confianza": round(confianza, 3), "alternativas": [{"clase": c, "confianza": round(p, 3)} for c, p in top[1:]]}
        )
    return casillas


def _vista_anotada(imagen: np.ndarray, esquinas: np.ndarray, margen: float, casillas: list[dict]) -> np.ndarray:
    """El tablero enderezado de una cámara con las piezas de `casillas` marcadas (verde ≥ 0.8, ámbar ≥ 0.5, rojo menos)."""
    vista = imagen_control_ampliada(imagen, esquinas) if not margen else dibujar_grilla_debug(enderezar_tablero(imagen, esquinas))
    borde = vista.shape[0] * 0.12 if not margen else 0
    paso = (vista.shape[0] - 2 * borde) / 8
    for c in casillas:
        clase, confianza, nombre = c["clase"], c["confianza"], c["casilla"]
        columna, fila = "abcdefgh".index(nombre[0]), 8 - int(nombre[1])
        if c.get("acuerdo") is False:  # las cámaras no coinciden en esta casilla: cuadro magenta (aunque quede vacía)
            x0, y0 = int(borde + columna * paso), int(borde + fila * paso)
            cv2.rectangle(vista, (x0 + 3, y0 + 3), (int(x0 + paso) - 3, int(y0 + paso) - 3), (255, 0, 255), 3)
        if clase == CLASE_VACIA:
            continue
        x, y = int(borde + (columna + 0.5) * paso), int(borde + (fila + 0.5) * paso)
        color = (0, 200, 0) if confianza >= 0.8 else (0, 190, 255) if confianza >= 0.5 else (0, 0, 255)
        cv2.circle(vista, (x, y), int(paso * 0.3), color, -1)
        cv2.putText(vista, _etiqueta_corta(clase), (x - 12, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255) if clase.startswith("black") else (0, 0, 0), 2, cv2.LINE_AA)
    return vista


def _probabilidades_dos_vistas(fotos: dict[str, np.ndarray]):
    """`(probs (64, clases), nombres, lecturas)` con el modelo de las dos vistas; `lecturas` = `(imagen, camara, recortes, esquinas, margen)` por cámara."""
    modo = piezas.modo_dos_vistas()
    lecturas = []
    for camara, imagen in fotos.items():
        try:
            recortes, esquinas, margen = recortes_de_imagen(imagen, camara, modo)
        except ValueError:
            continue
        lecturas.append((imagen, camara, recortes, esquinas, margen))
    if not lecturas:
        raise ValueError("No se detectó el tablero en ninguna cámara")
    nombres = list(lecturas[0][2])
    probs = piezas.probabilidades_dos_vistas({camara: [recortes[n] for n in nombres] for _, camara, recortes, _, _ in lecturas})
    return probs, nombres, lecturas


def dibujar_piezas_3d(imagen: np.ndarray, camara: str, casillas: list[dict], ancho_maximo: int = 900) -> np.ndarray:
    """La imagen ORIGINAL de la cámara, recortada alrededor del tablero, con la caja 3D (casilla × altura de la pieza) de cada pieza reconocida y su letra encima.

    Color de la caja: verde si la confianza es ≥ 0.8, ámbar ≥ 0.5, rojo menos. Muestra de un vistazo si cada pieza quedó en la casilla correcta
    y si la geometría (lente y posición de la cámara) coincide con las piezas reales. Lanza `ValueError` si la cámara no está calibrada.
    """
    from backend.servicios.vision import geometria3d

    esquinas, margen = esquinas_y_margen(imagen, camara)
    if margen:
        raise ValueError("La cámara no está calibrada: no se pueden dibujar las cajas 3D")
    alto, ancho = imagen.shape[:2]
    cajas = geometria3d.cajas_proyectadas(esquinas[::-1], geometria3d.cargar_lente(camara, ancho, alto))  # a8,h8,h1,a1 -> a1,h1,h8,a8
    salida = imagen.copy()
    for c in casillas:
        if c["clase"] == CLASE_VACIA:
            continue
        p = cajas[c["casilla"]].astype(int)
        color = (0, 200, 0) if c["confianza"] >= 0.8 else (0, 190, 255) if c["confianza"] >= 0.5 else (0, 0, 255)
        for i in range(4):
            cv2.line(salida, tuple(p[i]), tuple(p[(i + 1) % 4]), color, 2)
            cv2.line(salida, tuple(p[4 + i]), tuple(p[4 + (i + 1) % 4]), color, 2)
            cv2.line(salida, tuple(p[i]), tuple(p[4 + i]), color, 1)
        x, y = (int(v) for v in p[4:].mean(axis=0))
        cv2.circle(salida, (x, y), 14, color, -1)
        cv2.putText(salida, _etiqueta_corta(c["clase"]), (x - 9, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255) if c["clase"].startswith("black") else (0, 0, 0), 2, cv2.LINE_AA)
    todos = np.vstack(list(cajas.values()))  # recorta alrededor del tablero (con su altura): así ocupa toda la imagen y se ve más grande
    holgura = 0.04 * max(ancho, alto)
    x0, y0 = (max(0, int(v - holgura)) for v in todos.min(axis=0))
    x1, y1 = (int(v + holgura) for v in todos.max(axis=0))
    salida = salida[y0:min(alto, y1), x0:min(ancho, x1)]
    if salida.shape[1] > ancho_maximo:
        salida = cv2.resize(salida, (ancho_maximo, round(salida.shape[0] * ancho_maximo / salida.shape[1])))
    return salida


def probabilidades_de_piezas(fotos: dict[str, np.ndarray]) -> tuple[np.ndarray, list[str], list[str]]:
    """Probabilidades `(64, clases)` de las 13 clases por casilla con TODAS las cámaras de `fotos`, los nombres de casilla (a8 … h1) y los de las clases.

    Usa el modelo de dos vistas si existe; si no, el de una vista en cada cámara y los fusiona (ver `fusion`).

    Raises:
        FileNotFoundError: no hay ningún modelo de piezas entrenado. ValueError: tablero no detectado en ninguna cámara.
    """
    if piezas.hay_dos_vistas():
        probs, nombres, _ = _probabilidades_dos_vistas(fotos)
        return probs, nombres, piezas.clases_dos_vistas()
    lecturas = []
    ocupadas = ocupadas_de_arriba(fotos)
    for camara, imagen in fotos.items():
        try:
            lecturas.append(probabilidades_de_camara(imagen, camara, ocupadas))
        except ValueError:
            continue
    if not lecturas:
        raise ValueError("No se detectó el tablero en ninguna cámara")
    return fusionar_probabilidades([l[0] for l in lecturas]), lecturas[0][1], piezas.clases_del_modelo()


def _analizar_dos_vistas(fotos: dict[str, np.ndarray]) -> tuple[np.ndarray, list[dict]]:
    """Reconoce con el modelo entrenado con las dos cámaras a la vez: una sola decisión por casilla a partir de los dos recortes (ver `RedDosVistas`).

    Con una sola cámara la otra vista se anula. Devuelve lo mismo que `analizar_camaras`, sin el detalle por cámara (el modelo no decide por separado).
    """
    probs, nombres, lecturas = _probabilidades_dos_vistas(fotos)
    casillas = _casillas_de_probabilidades(probs, nombres, piezas.clases_dos_vistas(), fotos)
    vistas = [_vista_anotada(imagen, esquinas, margen, casillas) for imagen, _, _, esquinas, margen in lecturas]
    return (vistas[0] if len(vistas) == 1 else np.hstack(vistas)), casillas


def componer_vista_piezas(vista_plana: np.ndarray, fotos: dict[str, np.ndarray], casillas: list[dict], vista: str) -> np.ndarray:
    """Elige qué se muestra del reconocimiento: `plana` (el tablero enderezado), `cajas` (la imagen de cada cámara con la caja 3D de cada pieza) o `ambas` (cajas arriba, plana abajo).

    Si ninguna cámara se puede dibujar en 3D (sin calibrar), devuelve la vista plana.
    """
    if vista == "plana":
        return vista_plana
    cajas = []
    for camara, imagen in fotos.items():
        try:
            cajas.append(dibujar_piezas_3d(imagen, camara, casillas))
        except ValueError:
            continue
    if not cajas:
        return vista_plana
    alto = min(c.shape[0] for c in cajas)
    fila = np.hstack([cv2.resize(c, (round(c.shape[1] * alto / c.shape[0]), alto)) for c in cajas])
    if vista == "cajas":
        return fila
    ancho = max(fila.shape[1], vista_plana.shape[1])
    ajustadas = [cv2.resize(i, (ancho, round(i.shape[0] * ancho / i.shape[1]))) for i in (fila, vista_plana)]
    return np.vstack(ajustadas)


def analizar_tablero(imagen: np.ndarray, camara: str = "principal") -> tuple[np.ndarray, list[dict]]:
    """Reconoce las 64 casillas de `imagen` y devuelve `(imagen anotada BGR, predicciones por casilla)`."""
    if piezas.hay_dos_vistas():
        return _analizar_dos_vistas({camara: imagen})
    probs, nombres, esquinas, margen = probabilidades_de_camara(imagen, camara, ocupadas_de_arriba({camara: imagen}))
    casillas = _casillas_de_probabilidades(probs, nombres, fotos={camara: imagen})
    return _vista_anotada(imagen, esquinas, margen, casillas), casillas


def analizar_camaras(fotos: dict[str, np.ndarray]) -> tuple[np.ndarray, list[dict]]:
    """Reconoce el tablero con TODAS las cámaras de `fotos` ({camara: imagen}) y fusiona las probabilidades (producto de las probabilidades, ver `fusion`).

    Devuelve `(imagen, casillas)`: la imagen junta, lado a lado, la vista de cada cámara marcada con el resultado FUSIONADO (el mismo
    en todas, y un cuadro magenta en las casillas donde las cámaras no coinciden), y `casillas` las predicciones fusionadas; cada una trae
    `acuerdo` (si todas las cámaras coinciden) y `por_camara` (qué clase vio cada una). Una cámara cuyo tablero no se detecta se omite;
    si ninguna sirve, lanza `ValueError`.
    """
    if piezas.hay_dos_vistas():
        return _analizar_dos_vistas(fotos)
    lecturas = []
    ocupadas = ocupadas_de_arriba(fotos)
    for camara, imagen in fotos.items():
        try:
            lecturas.append((imagen, *probabilidades_de_camara(imagen, camara, ocupadas)))
        except ValueError:
            continue
    if not lecturas:
        raise ValueError("No se detectó el tablero en ninguna cámara")
    matrices = [probs for _, probs, *_ in lecturas]
    nombres = lecturas[0][2]
    casillas = _casillas_de_probabilidades(fusionar_probabilidades(matrices), nombres, fotos=fotos)
    if len(lecturas) > 1:
        clases_por_camara = [[top[0][0] for top in piezas.mejores_clases(m)] for m in matrices]
        for i, (c, desacuerdo) in enumerate(zip(casillas, casillas_en_desacuerdo(matrices))):
            c["acuerdo"] = not desacuerdo
            c["por_camara"] = [clases[i] for clases in clases_por_camara]
    vistas = [_vista_anotada(imagen, esquinas, margen, casillas) for imagen, _, _, esquinas, margen in lecturas]
    return (vistas[0] if len(vistas) == 1 else np.hstack(vistas)), casillas


def probar_tablero(imagen: np.ndarray | None = None) -> dict:
    """Reconoce el tablero (de la foto dada o de una nueva de la cámara principal) y devuelve predicciones e imagen en base64.

    Returns:
        `{"casillas": [{casilla, clase, confianza, alternativas}], "imagen": <JPEG en base64>}`; solo las casillas con pieza llevan
        etiqueta en la imagen.

    Raises:
        ValueError: tablero no detectado. RuntimeError: la cámara no está disponible.
    """
    if imagen is None:
        imagen = capturar_foto_tablero()
    vista, casillas = analizar_tablero(imagen)
    exito, buffer = cv2.imencode(".jpg", vista)
    if not exito:
        raise RuntimeError("No se pudo codificar la imagen")
    return {"casillas": casillas, "imagen": base64.b64encode(buffer.tobytes()).decode("ascii")}
