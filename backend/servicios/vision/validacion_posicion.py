"""Validaciones de la posición del tablero que no dependen de cómo se ven las piezas.

La visión se equivoca, pero la partida tiene reglas: se sabe cómo empieza, cada jugada solo puede ir a unas pocas casillas y el material
nunca aumenta. Estas funciones usan ese conocimiento para comprobar lo que ven las cámaras (`comparar_con_esperada`) y para descartar
posiciones imposibles (`problemas_de_posicion`, `material_imposible`).
"""
from __future__ import annotations

import chess
import numpy as np

from backend.servicios.vision.jugada_probable import NOMBRES, Lectura, _clase
from backend.servicios.vision.modelo_piezas import CLASE_VACIA

MAX_CASI = 2
"""Cuántas casillas distintas de lo esperado se toleran para decir que «casi coincide» (se muestran para confirmarlas a mano)."""

_PROBLEMAS_DE_ESTADO = (
    (chess.STATUS_NO_WHITE_KING, "Falta el rey blanco"),
    (chess.STATUS_NO_BLACK_KING, "Falta el rey negro"),
    (chess.STATUS_TOO_MANY_KINGS, "Hay más de un rey de un mismo color"),
    (chess.STATUS_PAWNS_ON_BACKRANK, "Hay peones en la primera o en la última fila"),
    (chess.STATUS_TOO_MANY_WHITE_PAWNS, "Hay más de 8 peones blancos"),
    (chess.STATUS_TOO_MANY_BLACK_PAWNS, "Hay más de 8 peones negros"),
    (chess.STATUS_TOO_MANY_WHITE_PIECES, "Hay más de 16 piezas blancas"),
    (chess.STATUS_TOO_MANY_BLACK_PIECES, "Hay más de 16 piezas negras"),
    (chess.STATUS_OPPOSITE_CHECK, "El bando que no mueve está en jaque"),
    (chess.STATUS_TOO_MANY_CHECKERS, "El rey recibe jaque de demasiadas piezas a la vez"),
    (chess.STATUS_IMPOSSIBLE_CHECK, "El jaque no puede haberse dado así"),
)
_INICIALES = {chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1}


def _lectura(lecturas: list[Lectura], marca: str) -> Lectura | None:
    return next((l for l in lecturas if marca in l.clases), None)


def comparar_con_esperada(fen_esperado: str, lecturas: list[Lectura]) -> dict:
    """Compara lo que ven las cámaras con la posición que debería haber (la inicial al arrancar, o la de la partida para resincronizar).

    La ocupación (vacía/blanca/negra) es lo que decide, porque es lo más fiable; el tipo de pieza solo se informa como aviso.

    Returns:
        `{"estado", "coinciden", "total", "discrepancias", "avisos_tipo"}`. `estado` es `coincide` (ninguna casilla distinta), `casi` (hasta
        `MAX_CASI`: se piden confirmar a mano) o `no_coincide`. Cada discrepancia es `{"casilla", "esperada", "vista", "confianza"}` y cada aviso
        de tipo `{"casilla", "esperada", "vista"}` (casillas con la ocupación correcta pero otra clase de pieza).

    Raises:
        ValueError: si no hay una lectura de ocupación.
    """
    ocupacion = _lectura(lecturas, "blanca")
    if ocupacion is None:
        raise ValueError("Hace falta la lectura de ocupación para comparar con la posición esperada")
    esperado = chess.Board(fen_esperado)
    piezas = [esperado.piece_at(chess.parse_square(nombre)) for nombre in NOMBRES]
    probs = np.asarray(ocupacion.probabilidades)
    vistas = probs.argmax(axis=1)
    discrepancias = []
    for i, nombre in enumerate(NOMBRES):
        pedida = _clase(piezas[i], ocupacion.clases)
        if vistas[i] != pedida:
            discrepancias.append({"casilla": nombre, "esperada": ocupacion.clases[pedida], "vista": ocupacion.clases[vistas[i]], "confianza": round(float(probs[i, vistas[i]]), 3)})
    avisos = []
    lectura_piezas = _lectura(lecturas, "white-pawn")
    if lectura_piezas is not None:
        vistas_piezas = np.asarray(lectura_piezas.probabilidades).argmax(axis=1)
        fallidas = {d["casilla"] for d in discrepancias}
        for i, nombre in enumerate(NOMBRES):
            if piezas[i] is None or nombre in fallidas:
                continue
            pedida = _clase(piezas[i], lectura_piezas.clases)
            if vistas_piezas[i] != pedida:
                avisos.append({"casilla": nombre, "esperada": lectura_piezas.clases[pedida], "vista": lectura_piezas.clases[vistas_piezas[i]]})
    cantidad = len(discrepancias)
    estado = "coincide" if cantidad == 0 else "casi" if cantidad <= MAX_CASI else "no_coincide"
    return {"estado": estado, "coinciden": 64 - cantidad, "total": 64, "discrepancias": discrepancias, "avisos_tipo": avisos}


def problemas_de_posicion(posicion: str | chess.Board) -> list[str]:
    """Razones por las que una posición no puede darse en una partida real (lista vacía si es posible).

    Además de lo que revisa `python-chess` (reyes, peones en la última fila, cantidad de piezas, jaques), comprueba que las piezas de más
    respecto de las iniciales (damas, torres, alfiles o caballos) se puedan explicar por peones coronados.
    """
    tablero = chess.Board(posicion) if isinstance(posicion, str) else posicion
    estado = tablero.status()
    problemas = [texto for bandera, texto in _PROBLEMAS_DE_ESTADO if estado & bandera]
    for color, nombre in ((chess.WHITE, "blancas"), (chess.BLACK, "negras")):
        coronadas = sum(max(0, len(tablero.pieces(tipo, color)) - inicial) for tipo, inicial in _INICIALES.items())
        if coronadas > 8 - len(tablero.pieces(chess.PAWN, color)):
            problemas.append(f"Hay más piezas {nombre} de las que pueden salir de las coronaciones")
    return problemas


def material_imposible(fen_antes: str, fen_despues: str) -> list[str]:
    """Qué cambio entre dos posiciones seguidas no puede ser de una sola jugada: el material nunca aumenta (salvo coronar un peón)."""
    antes, despues = chess.Board(fen_antes), chess.Board(fen_despues)
    problemas = []
    for color, nombre in ((chess.WHITE, "blancas"), (chess.BLACK, "negras")):
        peones_antes, peones_despues = len(antes.pieces(chess.PAWN, color)), len(despues.pieces(chess.PAWN, color))
        piezas_antes = sum(len(antes.pieces(t, color)) for t in _INICIALES)
        piezas_despues = sum(len(despues.pieces(t, color)) for t in _INICIALES)
        if peones_despues > peones_antes:
            problemas.append(f"Aparecieron peones {nombre}")
        if piezas_despues - piezas_antes > peones_antes - peones_despues:
            problemas.append(f"Aparecieron piezas {nombre} que no vienen de una coronación")
    return problemas



_INICIAL_POR_TIPO = {"queen": 1, "rook": 2, "bishop": 2, "knight": 2}
"""Cuántas hay al empezar de cada pieza que no es rey ni peón; solo se pueden tener más si algún peón coronó."""


def _filas_infractoras(asignadas: np.ndarray, clases: list[str]) -> list[int]:
    """Las casillas (filas) cuya clase rompe los límites de material de un bando; vacío si todo es posible.

    Los límites: un rey, hasta 8 peones, y las piezas de más respecto de las iniciales (2 torres, 2 alfiles, 2 caballos, 1 dama) no pueden
    superar los peones que faltan.
    """
    for color in ("white", "black"):
        por_tipo: dict[str, list[int]] = {}
        for fila, indice in enumerate(asignadas):
            clase = clases[indice]
            if clase.startswith(color):
                por_tipo.setdefault(clase.split("-")[1], []).append(fila)
        if len(por_tipo.get("king", [])) > 1:
            return por_tipo["king"]
        peones = por_tipo.get("pawn", [])
        if len(peones) > 8:
            return peones
        de_mas = {t: len(por_tipo.get(t, [])) - n for t, n in _INICIAL_POR_TIPO.items() if len(por_tipo.get(t, [])) > n}
        if sum(de_mas.values()) > 8 - len(peones):
            return [fila for t in de_mas for fila in por_tipo[t]]
    return []


def limitar_por_material(probs: np.ndarray, clases: list[str]) -> np.ndarray:
    """Probabilidades `(64, clases)` corregidas para que ninguna posición tenga más material del que puede haber en una partida.

    Un clasificador casilla por casilla puede ver tres reyes blancos o cinco alfiles negros. Mientras un bando rompa los límites (ver
    `_filas_infractoras`), la casilla infractora de menor confianza pierde esa clase y se queda con la siguiente más probable (la casilla vacía
    nunca se descarta). Devuelve una copia; las filas cambiadas se renormalizan. Sin las 13 clases del modelo de piezas, devuelve `probs` igual.
    """
    if CLASE_VACIA not in clases or "white-king" not in clases:
        return probs
    corregidas = np.array(probs, dtype=np.float64, copy=True)
    asignadas = corregidas.argmax(axis=1)
    for _ in range(corregidas.size):
        infractoras = _filas_infractoras(asignadas, clases)
        if not infractoras:
            break
        fila = min(infractoras, key=lambda f: corregidas[f, asignadas[f]])
        corregidas[fila, asignadas[fila]] = 0.0
        total = corregidas[fila].sum()
        if total > 0:
            corregidas[fila] /= total
        asignadas[fila] = corregidas[fila].argmax()
    return corregidas
