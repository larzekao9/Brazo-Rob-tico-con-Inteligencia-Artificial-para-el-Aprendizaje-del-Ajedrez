"""Wrapper sobre Stockfish (vía python-chess) para calcular y analizar jugadas."""
from __future__ import annotations

import os

import chess
import chess.engine

# Por defecto asume que "stockfish" está en el PATH del sistema (instalado con el
# paquete del sistema operativo). Si no, `STOCKFISH_PATH` en el entorno puede
# apuntar directo al ejecutable (ej. el binario oficial en `tools/stockfish/`,
# para no necesitar permisos de administrador en la máquina de cada quien).
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "stockfish")

# Rango del parámetro "Skill Level" de Stockfish.
NIVEL_MIN = 0
NIVEL_MAX = 20


def _validar_nivel(nivel: int) -> int:
    if not NIVEL_MIN <= nivel <= NIVEL_MAX:
        raise ValueError(f"nivel debe estar entre {NIVEL_MIN} y {NIVEL_MAX}, recibido {nivel}")
    return nivel


def _validar_fen(fen: str) -> chess.Board:
    """Construye el tablero y rechaza posiciones imposibles antes de tocar Stockfish.

    Sin esto, una posición sintácticamente válida pero imposible (ej. 9
    damas de un lado — puede pasar con un FEN mal reconocido por visión)
    hace que Stockfish se caiga con un error de proceso en vez de devolver
    un error claro y manejable.
    """
    try:
        tablero = chess.Board(fen)
    except ValueError as error:
        raise ValueError(f"FEN inválido: {fen}") from error
    if not tablero.is_valid():
        raise ValueError(f"Posición imposible en una partida real: {fen}")
    return tablero


def calcular_jugada(fen: str, nivel: int = 20, tiempo_limite: float = 1.0) -> str:
    """Calcula la jugada elegida por Stockfish para una posición dada.

    Args:
        fen: posición en notación FEN.
        nivel: fuerza de juego de Stockfish (0-20, "Skill Level").
        tiempo_limite: tiempo máximo de cálculo en segundos.

    Returns:
        La jugada elegida en notación SAN (ej. "e4", "Nf3").
    """
    _validar_nivel(nivel)
    tablero = _validar_fen(fen)
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as motor:
        motor.configure({"Skill Level": nivel})
        resultado = motor.play(tablero, chess.engine.Limit(time=tiempo_limite))
        if resultado.move is None:
            raise RuntimeError("Stockfish no devolvió una jugada")
        return tablero.san(resultado.move)


def analizar_posicion(
    fen: str, nivel: int = 20, tiempo_limite: float = 1.0, num_variaciones: int = 3
) -> dict:
    """Analiza una posición y devuelve la evaluación de Stockfish.

    Pide de una sola vez `num_variaciones` líneas (MultiPV) — así la mejor
    jugada y las candidatas alternativas (RF21) salen de un único análisis,
    sin abrir el proceso de Stockfish dos veces.

    Returns:
        dict con "jugada" (SAN de la mejor jugada), "evaluacion_cp"
        (centipawns desde el punto de vista del jugador a mover, None si hay
        mate forzado), "mate_en" (jugadas hasta el mate, None si no aplica),
        "profundidad" y "nodos" (cuánto pudo buscar Stockfish en el tiempo
        dado, None si el motor no los reportó), "variacion_principal" (la
        línea completa que analizó la mejor jugada, en SAN) y
        "variantes_candidatas" (lista de `{"jugada", "evaluacion_cp",
        "mate_en"}` con las siguientes mejores alternativas, de mejor a
        peor — ver `obtener_variaciones` para la misma información como
        función independiente).
    """
    _validar_nivel(nivel)
    tablero = _validar_fen(fen)
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as motor:
        motor.configure({"Skill Level": nivel})
        lineas = motor.analyse(tablero, chess.engine.Limit(time=tiempo_limite), multipv=num_variaciones)
        mejor_linea = lineas[0]
        score = mejor_linea["score"].pov(tablero.turn)
        variacion = mejor_linea.get("pv") or []
        mejor_jugada = variacion[0] if variacion else None

        variacion_principal = []
        tablero_variacion = tablero.copy()
        for jugada in variacion:
            variacion_principal.append(tablero_variacion.san(jugada))
            tablero_variacion.push(jugada)

        return {
            "jugada": tablero.san(mejor_jugada) if mejor_jugada else None,
            "evaluacion_cp": score.score(),
            "mate_en": score.mate(),
            "profundidad": mejor_linea.get("depth"),
            "nodos": mejor_linea.get("nodes"),
            "variacion_principal": variacion_principal,
            "variantes_candidatas": _lineas_a_variantes(lineas, tablero),
        }


def _lineas_a_variantes(lineas: list[dict], tablero: chess.Board) -> list[dict]:
    """Convierte las líneas de un análisis MultiPV en `{"jugada", "evaluacion_cp", "mate_en"}`."""
    variantes = []
    for linea in lineas:
        pv = linea.get("pv") or []
        if not pv:
            continue
        score_linea = linea["score"].pov(tablero.turn)
        variantes.append({
            "jugada": tablero.san(pv[0]),
            "evaluacion_cp": score_linea.score(),
            "mate_en": score_linea.mate(),
        })
    return variantes


def obtener_variaciones(
    fen: str, nivel: int = 20, num_variaciones: int = 3, tiempo_limite: float = 1.0
) -> list[dict]:
    """Devuelve las mejores jugadas candidatas para una posición, con su evaluación (RF21).

    Args:
        fen: posición en notación FEN.
        nivel: fuerza de juego de Stockfish (0-20, "Skill Level").
        num_variaciones: cantidad de jugadas candidatas a devolver (MultiPV).
        tiempo_limite: tiempo máximo de cálculo en segundos.

    Returns:
        Lista de `{"jugada": str, "evaluacion_cp": int | None, "mate_en": int | None}`,
        ordenada de mejor a peor.
    """
    _validar_nivel(nivel)
    tablero = _validar_fen(fen)
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as motor:
        motor.configure({"Skill Level": nivel})
        lineas = motor.analyse(
            tablero,
            chess.engine.Limit(time=tiempo_limite),
            multipv=num_variaciones,
        )
        return _lineas_a_variantes(lineas, tablero)
