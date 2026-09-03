"""Convierte partidas PGN de Lichess en tensores de entrada para el modelo.

Codificación de posición: 8x8x12, siempre desde la perspectiva del jugador a
mover (si le toca a negras, el tablero se rota 180°) — así el modelo aprende
un solo patrón en vez de duplicarlo por color. Las primeras 6 capas son las
piezas propias, las últimas 6 las del rival, en orden peón/caballo/alfil/
torre/dama/rey.

Codificación de etiqueta: `from_square * 64 + to_square` (4096 clases), en la
misma perspectiva rotada que el tensor. No distingue subpromociones (dama,
torre, alfil o caballo cuentan como la misma clase) — simplificación
deliberada para la primera versión del pipeline.
"""
from __future__ import annotations

import io
from pathlib import Path

import chess
import chess.pgn
import numpy as np
import zstandard as zstd

PIEZAS_ORDEN = [
    chess.PAWN,
    chess.KNIGHT,
    chess.BISHOP,
    chess.ROOK,
    chess.QUEEN,
    chess.KING,
]


def _square_en_perspectiva(square: int, color_a_mover: bool) -> int:
    """Rota una casilla 180° si le toca mover a negras, si no la deja igual."""
    return square if color_a_mover == chess.WHITE else 63 - square


def board_to_tensor(board: chess.Board) -> np.ndarray:
    """Codifica un tablero como tensor (8, 8, 12) desde la óptica del jugador a mover."""
    tensor = np.zeros((8, 8, 12), dtype=np.float32)
    color_a_mover = board.turn
    for square in chess.SQUARES:
        pieza = board.piece_at(square)
        if pieza is None:
            continue
        square_rotado = _square_en_perspectiva(square, color_a_mover)
        fila, columna = divmod(square_rotado, 8)
        indice_pieza = PIEZAS_ORDEN.index(pieza.piece_type)
        offset_color = 0 if pieza.color == color_a_mover else 6
        tensor[fila, columna, indice_pieza + offset_color] = 1.0
    return tensor


def jugada_a_etiqueta(board: chess.Board, jugada: chess.Move) -> int:
    """Codifica una jugada legal como índice de clase (0-4095), en perspectiva del mover."""
    color_a_mover = board.turn
    origen = _square_en_perspectiva(jugada.from_square, color_a_mover)
    destino = _square_en_perspectiva(jugada.to_square, color_a_mover)
    return origen * 64 + destino


def pgn_to_samples(path: str | Path, limite_partidas: int) -> list[tuple[np.ndarray, int]]:
    """Lee un `.pgn.zst` de Lichess y devuelve pares (tensor, etiqueta) de sus jugadas.

    Args:
        path: ruta al archivo `.pgn.zst` (se descomprime en streaming, sin
            volcar el archivo completo a disco).
        limite_partidas: cantidad de partidas a procesar desde el inicio del
            archivo.

    Returns:
        Lista de pares (tensor de la posición antes de la jugada, etiqueta de
        la jugada jugada por el humano).
    """
    muestras: list[tuple[np.ndarray, int]] = []
    descompresor = zstd.ZstdDecompressor()
    with open(path, "rb") as comprimido, descompresor.stream_reader(comprimido) as flujo_binario:
        flujo_texto = io.TextIOWrapper(flujo_binario, encoding="utf-8", errors="replace")
        partidas_leidas = 0
        while partidas_leidas < limite_partidas:
            partida = chess.pgn.read_game(flujo_texto)
            if partida is None:
                break
            tablero = partida.board()
            for jugada in partida.mainline_moves():
                muestras.append((board_to_tensor(tablero), jugada_a_etiqueta(tablero, jugada)))
                tablero.push(jugada)
            partidas_leidas += 1
    return muestras
