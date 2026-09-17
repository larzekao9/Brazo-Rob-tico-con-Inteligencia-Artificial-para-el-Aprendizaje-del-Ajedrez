"""Evaluación real del modelo de jugadas (HU4): accuracy top-1 contra partidas humanas
que el modelo nunca vio en entrenamiento, y clasificación de qué tan caro sale en
centipawns cuando no acierta.

División train/val por partida completa: `evaluar_modelo` arranca en `saltar_partidas`
(las primeras N, ya usadas por `training/colab_entrenamiento.ipynb` para entrenar) y
evalúa las siguientes. La v1 del modelo usó un split aleatorio 90/10 por posición
suelta, que filtra información entre train y val porque dos posiciones de la misma
partida terminan una en cada lado — acá no se repite ese error.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.pgn
import zstandard as zstd

from backend.servicios.aprendizaje.inferencia import RUTA_CHECKPOINT_POR_DEFECTO, predecir_jugada
from backend.servicios.motor.motor_ajedrez import analizar_posicion

EVAL_MATE_CP = 10000

BALDES_ERROR = ("aceptable", "imprecision", "error", "blunder")

DATASET_POR_DEFECTO = Path(__file__).resolve().parent / "data" / "lichess_db_standard_rated_2017-02.pgn.zst"


def partidas_desde(ruta_pgn: str | Path, saltar_partidas: int, cantidad_partidas: int):
    """Generador de partidas de un `.pgn.zst`, saltando las primeras `saltar_partidas`.

    Lee en streaming, igual que `pgn_to_samples` en `data_pipeline.py`. Saltar con
    `chess.pgn.skip_game` evita construir el árbol de jugadas de las partidas que no
    interesan (las ya usadas para entrenar).
    """
    descompresor = zstd.ZstdDecompressor()
    with open(ruta_pgn, "rb") as comprimido, descompresor.stream_reader(comprimido) as flujo_binario:
        flujo_texto = io.TextIOWrapper(flujo_binario, encoding="utf-8", errors="replace")
        for _ in range(saltar_partidas):
            if not chess.pgn.skip_game(flujo_texto):
                return
        partidas_devueltas = 0
        while partidas_devueltas < cantidad_partidas:
            partida = chess.pgn.read_game(flujo_texto)
            if partida is None:
                return
            yield partida
            partidas_devueltas += 1


def clasificar_perdida_cp(perdida_cp: int) -> str:
    """Clasifica una pérdida de centipawns en los mismos baldes que usa Lichess para
    inaccuracy/mistake/blunder (50/100/300 cp), con un balde extra "aceptable" para no
    contar como error diferencias de evaluación demasiado chicas para importar.
    """
    if perdida_cp < 50:
        return "aceptable"
    if perdida_cp < 100:
        return "imprecision"
    if perdida_cp < 300:
        return "error"
    return "blunder"


def _valor_cp(resultado_analisis: dict) -> int:
    """Extrae un valor en centipawns de `analizar_posicion`, con un tope grande para mate."""
    if resultado_analisis["evaluacion_cp"] is not None:
        return resultado_analisis["evaluacion_cp"]
    return EVAL_MATE_CP if resultado_analisis["mate_en"] > 0 else -EVAL_MATE_CP


def perdida_cp_de_jugada(
    fen_antes: str,
    jugada_san: str,
    nivel_stockfish: int = 10,
    tiempo_limite_stockfish: float = 0.1,
) -> int:
    """Mide cuánto pierde `jugada_san` en centipawns respecto a la mejor jugada de Stockfish
    en `fen_antes`, siempre en perspectiva de quien decidió `jugada_san`.

    `analizar_posicion` devuelve la evaluación en perspectiva del jugador a mover en esa
    posición puntual — antes de la jugada eso ya es la perspectiva que queremos, pero
    después de la jugada le toca mover al rival, así que hay que invertir el signo.
    """
    tablero = chess.Board(fen_antes)
    eval_mejor = _valor_cp(analizar_posicion(fen_antes, nivel_stockfish, tiempo_limite_stockfish))

    tablero.push(tablero.parse_san(jugada_san))
    if tablero.is_game_over():
        eval_tras_jugada = EVAL_MATE_CP if tablero.is_checkmate() else 0
    else:
        resultado_rival = analizar_posicion(tablero.fen(), nivel_stockfish, tiempo_limite_stockfish)
        eval_tras_jugada = -_valor_cp(resultado_rival)

    return max(0, eval_mejor - eval_tras_jugada)


@dataclass
class ResultadoEvaluacion:
    total_jugadas: int
    aciertos: int
    distribucion_errores: dict[str, int]

    @property
    def accuracy(self) -> float:
        return self.aciertos / self.total_jugadas if self.total_jugadas else 0.0


def evaluar_modelo(
    ruta_pgn: str | Path,
    cantidad_partidas: int = 20,
    saltar_partidas: int = 200,
    ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO,
    nivel_stockfish: int = 10,
    tiempo_limite_stockfish: float = 0.1,
) -> ResultadoEvaluacion:
    """Recorre jugadas humanas reales y compara cada una con la predicción del modelo.

    Cada desacierto dispara una o dos llamadas a Stockfish (posición antes y, si la
    jugada del modelo no termina la partida, posición después) para medir qué tan caro
    salió en centipawns — por eso `cantidad_partidas` conviene mantenerlo chico.
    """
    total_jugadas = 0
    aciertos = 0
    distribucion_errores = {balde: 0 for balde in BALDES_ERROR}

    for partida in partidas_desde(ruta_pgn, saltar_partidas, cantidad_partidas):
        tablero = partida.board()
        for jugada_humana in partida.mainline_moves():
            fen_antes = tablero.fen()
            jugada_humana_san = tablero.san(jugada_humana)
            jugada_modelo_san = predecir_jugada(fen_antes, ruta_checkpoint)

            total_jugadas += 1
            if jugada_modelo_san == jugada_humana_san:
                aciertos += 1
            else:
                perdida_cp = perdida_cp_de_jugada(
                    fen_antes, jugada_modelo_san, nivel_stockfish, tiempo_limite_stockfish
                )
                distribucion_errores[clasificar_perdida_cp(perdida_cp)] += 1

            tablero.push(jugada_humana)

    return ResultadoEvaluacion(total_jugadas, aciertos, distribucion_errores)


if __name__ == "__main__":
    resultado = evaluar_modelo(DATASET_POR_DEFECTO, cantidad_partidas=20)
    print(f"jugadas evaluadas: {resultado.total_jugadas}")
    print(f"accuracy top-1: {resultado.accuracy:.2%}")
    print("distribución de errores (sobre las jugadas que no coincidieron):")
    for balde in BALDES_ERROR:
        print(f"  {balde}: {resultado.distribucion_errores[balde]}")
