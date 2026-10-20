"""Detecta qué jugada se hizo comparando el tablero de antes y de después de
una foto (HU1, RF11).

No hace falta un modelo nuevo para esto: alcanza con probar, entre todas las
jugadas legales de la posición "antes", cuál termina exactamente en la
ubicación de piezas de la posición "después". Es la forma estándar de
resolver esto en ajedrez por cámara — más simple y más confiable que tratar
de leer la jugada directamente de la imagen.
"""
from __future__ import annotations

import chess


def detectar_jugada(fen_antes: str, fen_despues: str) -> str | None:
    """Encuentra la jugada legal que lleva de `fen_antes` a `fen_despues`.

    Solo compara la ubicación de piezas (primer campo del FEN) — el turno,
    el enroque y el al paso no se pueden leer de forma confiable de una
    foto (ver `reconocimiento.py`), así que no se usan para decidir.

    Args:
        fen_antes: FEN reconocido antes de la jugada (el turno importa acá:
            determina de quién son las jugadas legales a probar).
        fen_despues: FEN reconocido después de la jugada.

    Returns:
        La jugada encontrada, en notación SAN, o `None` si ninguna jugada
        legal explica la diferencia (ruido de reconocimiento, o no hubo
        ninguna jugada entre las dos fotos).
    """
    tablero = chess.Board(fen_antes)
    piezas_despues = fen_despues.split(" ")[0]

    for jugada in list(tablero.legal_moves):
        jugada_san = tablero.san(jugada)
        tablero.push(jugada)
        coincide = tablero.fen().split(" ")[0] == piezas_despues
        tablero.pop()
        if coincide:
            return jugada_san
    return None


def ocupacion_de_tablero(tablero: chess.Board) -> dict[str, str]:
    """`{casilla: "vacia" | "blanca" | "negra"}` de las 64 casillas de un tablero."""
    mapa = {}
    for casilla in chess.SQUARES:
        pieza = tablero.piece_at(casilla)
        mapa[chess.square_name(casilla)] = "vacia" if pieza is None else ("blanca" if pieza.color == chess.WHITE else "negra")
    return mapa


def detectar_jugada_por_ocupacion(fen_antes: str, observada: dict[str, str], max_diferencias: int = 1) -> str | None:
    """Encuentra la jugada legal cuya ocupación (vacía/blanca/negra por casilla) mejor coincide con la observada en la foto.

    No hace falta saber de qué TIPO es cada pieza: la posición anterior se conoce, así que alcanza ver qué casillas cambiaron y de
    qué color quedaron. Tolera hasta `max_diferencias` casillas mal vistas, siempre que una sola jugada sea la más parecida
    (si dos jugadas empatan, o la mejor no supera a "no se movió nada", devuelve `None` en vez de adivinar).

    Returns:
        La jugada en SAN, o `None` si no se vio ninguna jugada o hay ambigüedad.
    """
    tablero = chess.Board(fen_antes)

    def distancia(mapa: dict[str, str]) -> int:
        return sum(mapa[c] != observada[c] for c in mapa)

    sin_mover = distancia(ocupacion_de_tablero(tablero))
    candidatas: dict[tuple, tuple[int, chess.Move]] = {}
    for jugada in tablero.legal_moves:
        tablero.push(jugada)
        mapa = ocupacion_de_tablero(tablero)
        tablero.pop()
        clave = tuple(sorted(mapa.items()))
        coronacion_menor = jugada.promotion not in (None, chess.QUEEN)
        if clave in candidatas and (coronacion_menor or candidatas[clave][1].promotion == chess.QUEEN):
            continue  # misma ocupación: se queda con la coronación a dama
        candidatas[clave] = (distancia(mapa), jugada)
    ordenadas = sorted(candidatas.values(), key=lambda par: par[0])
    if not ordenadas:
        return None
    mejor, jugada = ordenadas[0]
    segunda = ordenadas[1][0] if len(ordenadas) > 1 else 99
    if mejor > max_diferencias or segunda <= mejor or sin_mover <= mejor:
        return None
    return tablero.san(jugada)
