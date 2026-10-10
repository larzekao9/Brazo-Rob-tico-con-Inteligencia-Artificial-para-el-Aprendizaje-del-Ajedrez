"""Análisis jugada por jugada de una partida con la red propia (HU6 ampliada).

Recorre la partida desde su posición inicial y, en cada posición, le pregunta a la red
qué jugada elegiría (`predecir_top_jugadas`). Después compara esa elección con la jugada
que realmente se jugó. La red decide sola: acá solo se mide lo que hace en partidas reales,
sin usar Stockfish para decidir (regla 1 de CLAUDE.md).

Uso exclusivo del facilitador: ver `GET /partida/{id}/analisis-red`.
"""
from __future__ import annotations

from collections.abc import Callable

import chess

from backend.servicios.aprendizaje.inferencia import predecir_top_jugadas

TOP_N_POR_DEFECTO = 3

Predictor = Callable[[str, int], list[tuple[str, float]]]


def _predictor_por_defecto(fen: str, top_n: int) -> list[tuple[str, float]]:
    return predecir_top_jugadas(fen, top_n=top_n)


def _porcentaje(coinciden: int, total: int) -> float | None:
    return round(100 * coinciden / total, 1) if total else None


def _resumir(jugadas: list[dict]) -> dict:
    """Conteo de coincidencias de la red con las jugadas reales, en total y por lado."""

    def bloque(filtradas: list[dict]) -> dict:
        total = len(filtradas)
        coinciden = sum(1 for j in filtradas if j["coincide"])
        return {"total": total, "coinciden": coinciden, "porcentaje": _porcentaje(coinciden, total)}

    return {
        "total_jugadas": len(jugadas),
        "coinciden": sum(1 for j in jugadas if j["coincide"]),
        "porcentaje": _porcentaje(sum(1 for j in jugadas if j["coincide"]), len(jugadas)),
        "jugador": bloque([j for j in jugadas if j["quien"] == "jugador"]),
        "contraparte": bloque([j for j in jugadas if j["quien"] != "jugador"]),
    }


def analizar_partida_con_red(
    fen_inicial: str,
    jugadas_san: list[str],
    tipo_oponente: str,
    predictor: Predictor | None = None,
    top_n: int = TOP_N_POR_DEFECTO,
) -> dict:
    """Compara, jugada por jugada, la elección de la red con la jugada real.

    El humano juega blancas (ver `Partida`). Las negras son de la contraparte: `modelo` si
    `tipo_oponente` es "modelo", o `motor` en el resto de los casos.

    Args:
        fen_inicial: posición desde la que arrancó la partida.
        jugadas_san: jugadas en notación SAN, en orden.
        tipo_oponente: "motor" o "modelo" (quién juega las negras).
        predictor: función (fen, top_n) -> [(jugada_san, probabilidad)], ordenada de mayor a
            menor. Por defecto usa la red real; se inyecta en las pruebas.
        top_n: cuántas candidatas de la red se guardan por jugada.

    Returns:
        Dict con "jugadas" (detalle por jugada) y "resumen" (porcentajes de coincidencia).

    Raises:
        ValueError: si una jugada de `jugadas_san` no es legal en su posición.
        FileNotFoundError: si no existe el checkpoint de la red (y no se inyectó predictor).
    """
    predecir = predictor or _predictor_por_defecto
    tablero = chess.Board(fen_inicial)
    jugadas: list[dict] = []

    for numero, san in enumerate(jugadas_san, start=1):
        fen_antes = tablero.fen()
        mueven_blancas = tablero.turn == chess.WHITE
        candidatas = predecir(fen_antes, top_n)
        jugada_red, probabilidad_red = candidatas[0] if candidatas else (None, None)
        probabilidad_jugada = next((p for s, p in candidatas if s == san), None)

        movimiento = tablero.parse_san(san)
        tablero.push(movimiento)

        jugadas.append(
            {
                "numero": numero,
                "color": "blancas" if mueven_blancas else "negras",
                "quien": "jugador" if mueven_blancas else tipo_oponente,
                "fen_antes": fen_antes,
                "jugada": san,
                "jugada_uci": movimiento.uci(),
                "red_elige": jugada_red,
                "probabilidad_red": probabilidad_red,
                "probabilidad_jugada": probabilidad_jugada,
                "coincide": jugada_red == san,
                "candidatas": [{"jugada": s, "probabilidad": p} for s, p in candidatas],
            }
        )

    return {"jugadas": jugadas, "resumen": _resumir(jugadas)}
