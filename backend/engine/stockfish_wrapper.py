"""Wrapper sobre Stockfish (vía python-chess) para calcular y analizar jugadas."""
from __future__ import annotations

import chess
import chess.engine

STOCKFISH_PATH = "stockfish"

# Rango del parámetro "Skill Level" de Stockfish.
NIVEL_MIN = 0
NIVEL_MAX = 20


def _validar_nivel(nivel: int) -> int:
    if not NIVEL_MIN <= nivel <= NIVEL_MAX:
        raise ValueError(f"nivel debe estar entre {NIVEL_MIN} y {NIVEL_MAX}, recibido {nivel}")
    return nivel


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
    tablero = chess.Board(fen)
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as motor:
        motor.configure({"Skill Level": nivel})
        resultado = motor.play(tablero, chess.engine.Limit(time=tiempo_limite))
        if resultado.move is None:
            raise RuntimeError("Stockfish no devolvió una jugada")
        return tablero.san(resultado.move)


def analizar_posicion(fen: str, nivel: int = 20, tiempo_limite: float = 1.0) -> dict:
    """Analiza una posición y devuelve la evaluación de Stockfish.

    Returns:
        dict con "jugada" (SAN de la mejor jugada), "evaluacion_cp"
        (centipawns desde el punto de vista del jugador a mover, None si hay
        mate forzado) y "mate_en" (jugadas hasta el mate, None si no aplica).
    """
    _validar_nivel(nivel)
    tablero = chess.Board(fen)
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as motor:
        motor.configure({"Skill Level": nivel})
        info = motor.analyse(tablero, chess.engine.Limit(time=tiempo_limite))
        score = info["score"].pov(tablero.turn)
        variacion = info.get("pv") or []
        mejor_jugada = variacion[0] if variacion else None
        return {
            "jugada": tablero.san(mejor_jugada) if mejor_jugada else None,
            "evaluacion_cp": score.score(),
            "mate_en": score.mate(),
        }


def obtener_variaciones(
    fen: str, nivel: int = 20, num_variaciones: int = 3, tiempo_limite: float = 1.0
) -> list[str]:
    """Devuelve las mejores jugadas candidatas para una posición.

    Args:
        fen: posición en notación FEN.
        nivel: fuerza de juego de Stockfish (0-20, "Skill Level").
        num_variaciones: cantidad de jugadas candidatas a devolver (MultiPV).
        tiempo_limite: tiempo máximo de cálculo en segundos.

    Returns:
        Lista de jugadas en notación SAN, ordenadas de mejor a peor.
    """
    _validar_nivel(nivel)
    tablero = chess.Board(fen)
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as motor:
        motor.configure({"Skill Level": nivel})
        lineas = motor.analyse(
            tablero,
            chess.engine.Limit(time=tiempo_limite),
            multipv=num_variaciones,
        )
        return [tablero.san(linea["pv"][0]) for linea in lineas if linea.get("pv")]
