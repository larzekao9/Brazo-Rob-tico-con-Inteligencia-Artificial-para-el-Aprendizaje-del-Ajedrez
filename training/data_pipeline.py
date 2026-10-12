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
import random
from dataclasses import dataclass, field
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


def pgn_to_samples(
    path: str | Path,
    limite_partidas: int,
    elo_minimo: int | None = None,
    saltar_partidas: int = 0,
) -> list[tuple[np.ndarray, int]]:
    """Lee un `.pgn.zst` de Lichess y devuelve pares (tensor, etiqueta) de sus jugadas.

    Args:
        path: ruta al archivo `.pgn.zst` (se descomprime en streaming, sin
            volcar el archivo completo a disco).
        limite_partidas: cantidad máxima de partidas a procesar.
        elo_minimo: si se especifica, solo procesa partidas donde ambos
            jugadores tengan un ELO mayor o igual a este umbral (ej. 2000).
        saltar_partidas: cantidad de partidas a saltar al inicio del archivo
            antes de empezar a recolectar muestras.

    Returns:
        Lista de pares (tensor de la posición antes de la jugada, etiqueta de
        la jugada jugada por el humano).
    """
    muestras: list[tuple[np.ndarray, int]] = []
    descompresor = zstd.ZstdDecompressor()
    with open(path, "rb") as comprimido, descompresor.stream_reader(comprimido) as flujo_binario:
        flujo_texto = io.TextIOWrapper(flujo_binario, encoding="utf-8", errors="replace")

        # Saltar partidas iniciales si se solicita
        for _ in range(saltar_partidas):
            if not chess.pgn.skip_game(flujo_texto):
                return muestras

        partidas_leidas = 0
        while partidas_leidas < limite_partidas:
            partida = chess.pgn.read_game(flujo_texto)
            if partida is None:
                break

            # Filtrar por ELO si está configurado
            if elo_minimo is not None:
                try:
                    white_elo = int(partida.headers.get("WhiteElo", "0"))
                    black_elo = int(partida.headers.get("BlackElo", "0"))
                    if white_elo < elo_minimo or black_elo < elo_minimo:
                        continue
                except (ValueError, TypeError):
                    continue

            tablero = partida.board()
            for jugada in partida.mainline_moves():
                muestras.append((board_to_tensor(tablero), jugada_a_etiqueta(tablero, jugada)))
                tablero.push(jugada)
            partidas_leidas += 1

    return muestras



# ---------------------------------------------------------------------------
# Pipeline v6: conteo por ELO y extracción compacta con validación separada por partida
# ---------------------------------------------------------------------------
def _elos_de(headers) -> tuple[int, int] | None:
    """`(ELO de blancas, ELO de negras)` de los encabezados de una partida, o `None` si faltan o no son números."""
    try:
        return int(headers.get("WhiteElo", "0")), int(headers.get("BlackElo", "0"))
    except (ValueError, TypeError):
        return None


def contar_partidas_por_elo(
    path: str | Path,
    umbrales: tuple[int, ...] = (2000, 2200, 2400),
    limite_leidas: int | None = None,
) -> dict:
    """Cuenta cuántas partidas de un `.pgn.zst` tienen a AMBOS jugadores con ELO >= cada umbral.

    Solo lee los encabezados (no interpreta las jugadas), así que es mucho más rápido que extraer
    muestras. Sirve para decidir con datos cuántas partidas de maestros hay disponibles antes de entrenar.

    Args:
        path: ruta al archivo `.pgn.zst`.
        umbrales: ELO mínimos a contar (ambos jugadores).
        limite_leidas: si se indica, corta tras leer esa cantidad de partidas (conteo aproximado y rápido).

    Returns:
        `{"leidas": int, "con_elo": int, "por_umbral": {umbral: cantidad}}`.
    """
    por_umbral = {umbral: 0 for umbral in umbrales}
    leidas = 0
    con_elo = 0
    descompresor = zstd.ZstdDecompressor()
    with open(path, "rb") as comprimido, descompresor.stream_reader(comprimido) as flujo_binario:
        flujo_texto = io.TextIOWrapper(flujo_binario, encoding="utf-8", errors="replace")
        while limite_leidas is None or leidas < limite_leidas:
            headers = chess.pgn.read_headers(flujo_texto)
            if headers is None:
                break
            leidas += 1
            elos = _elos_de(headers)
            if elos is None or min(elos) <= 0:
                continue
            con_elo += 1
            menor = min(elos)
            for umbral in umbrales:
                if menor >= umbral:
                    por_umbral[umbral] += 1
    return {"leidas": leidas, "con_elo": con_elo, "por_umbral": por_umbral}


class _ConstructorSoloMaestros(chess.pgn.GameBuilder):
    """Construye la partida solo si ambos jugadores tienen ELO >= `elo_minimo`; si no, salta sus jugadas.

    Leer una partida completa con `chess.pgn.read_game` interpreta todas sus jugadas, y en un archivo de
    Lichess casi todas las partidas se descartan por ELO: en el de febrero 2017, solo ~1 de cada 80 tiene a
    ambos jugadores arriba de 2200. Devolver `SKIP` al terminar los encabezados evita interpretar las jugadas
    de las partidas descartadas, lo que acelera mucho la extracción (el resultado es el mismo).
    """

    def __init__(self, elo_minimo: int | None) -> None:
        super().__init__()
        self._elo_minimo = elo_minimo

    def end_headers(self):
        if self._elo_minimo is not None:
            elos = _elos_de(self.game.headers)
            if elos is None or min(elos) < self._elo_minimo:
                return getattr(chess.pgn, "SKIP", None)
        return None


@dataclass
class ExtraccionDividida:
    """Resultado de `pgn_a_muestras_divididas`.

    `partidas_crudas_leidas` es hasta qué partida del archivo (contando las que se descartaron por ELO)
    llegó la extracción: una evaluación honesta tiene que saltar al menos esa cantidad para no usar
    partidas que el modelo ya vio.
    """

    muestras_train: list = field(default_factory=list)
    muestras_val: list = field(default_factory=list)
    partidas_train: int = 0
    partidas_val: int = 0
    partidas_crudas_leidas: int = 0


def pgn_a_muestras_divididas(
    path: str | Path,
    limite_partidas: int,
    elo_minimo: int | None = None,
    fraccion_validacion: float = 0.05,
    semilla: int = 42,
    saltar_partidas: int = 0,
) -> ExtraccionDividida:
    """Como `pgn_to_samples`, pero separa entrenamiento y validación POR PARTIDA y guarda las posiciones en `uint8`.

    Dos diferencias deliberadas respecto de `pgn_to_samples` + mezclar posiciones:

    1. **Split por partida.** Cada partida entera va a entrenamiento o a validación. Si se mezclan
       posiciones sueltas, posiciones de la misma partida quedan de los dos lados y la precisión de
       validación sale inflada (el mismo error que ya se documentó en `evaluar_modelo`).
    2. **`uint8` en vez de `float32`.** Las posiciones son 0/1, así que ocupan 768 bytes en vez de 3072:
       cuatro veces menos memoria, lo que deja entrenar con millones de posiciones en Colab. Quien las
       use tiene que pasarlas a `float32` al armar cada lote.

    Args:
        path: ruta al `.pgn.zst`.
        limite_partidas: cantidad de partidas aceptadas (por ELO) a extraer, entre train y val.
        elo_minimo: ambos jugadores con ELO >= este valor.
        fraccion_validacion: proporción aproximada de partidas que van a validación.
        semilla: hace reproducible la asignación de cada partida a train o val.
        saltar_partidas: partidas iniciales del archivo a saltar.
    """
    azar = random.Random(semilla)
    resultado = ExtraccionDividida()
    descompresor = zstd.ZstdDecompressor()
    with open(path, "rb") as comprimido, descompresor.stream_reader(comprimido) as flujo_binario:
        flujo_texto = io.TextIOWrapper(flujo_binario, encoding="utf-8", errors="replace")
        for _ in range(saltar_partidas):
            if not chess.pgn.skip_game(flujo_texto):
                resultado.partidas_crudas_leidas = saltar_partidas
                return resultado
        resultado.partidas_crudas_leidas = saltar_partidas

        aceptadas = 0
        while aceptadas < limite_partidas:
            partida = chess.pgn.read_game(flujo_texto, Visitor=lambda: _ConstructorSoloMaestros(elo_minimo))
            if partida is None:
                break
            resultado.partidas_crudas_leidas += 1

            # Red de seguridad: si esta versión de python-chess no saltó la partida, se descarta igual.
            if elo_minimo is not None:
                elos = _elos_de(partida.headers)
                if elos is None or min(elos) < elo_minimo:
                    continue

            es_validacion = azar.random() < fraccion_validacion
            destino = resultado.muestras_val if es_validacion else resultado.muestras_train
            tablero = partida.board()
            for jugada in partida.mainline_moves():
                destino.append((board_to_tensor(tablero).astype(np.uint8), jugada_a_etiqueta(tablero, jugada)))
                tablero.push(jugada)
            aceptadas += 1
            if es_validacion:
                resultado.partidas_val += 1
            else:
                resultado.partidas_train += 1
    return resultado
