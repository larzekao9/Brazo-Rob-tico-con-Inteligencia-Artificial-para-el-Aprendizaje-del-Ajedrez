"""Inferencia del modelo de jugadas (HU4): carga el checkpoint entrenado en Colab
y predice la jugada más probable para una posición, entre las jugadas legales.

Esto nunca decide la jugada real de la partida (ver reglas del PAPs) — Stockfish
sigue siendo la única fuente de la jugada que se ejecuta. Este módulo es la base
para conectar el modelo propio a `EstrategiaJugada` (HU4) y a las explicaciones
de HU5.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import chess
import torch

from backend.servicios.aprendizaje.modelo_jugadas import RedPrediccionJugadas, tensor_a_entrada_red
from training.data_pipeline import board_to_tensor, jugada_a_etiqueta

RUTA_CHECKPOINT_POR_DEFECTO = Path("training/checkpoints/modelo_jugadas_v1_2026-09-14.pt")


@lru_cache(maxsize=None)
def cargar_modelo(ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO) -> RedPrediccionJugadas:
    """Carga los pesos del checkpoint y devuelve el modelo listo para inferencia.

    Cachea por ruta de checkpoint para no releer el archivo (26MB) en cada
    predicción — la app llama a esto una vez por partida como mucho.
    """
    checkpoint = torch.load(Path(ruta_checkpoint), map_location="cpu")
    modelo = RedPrediccionJugadas(cantidad_clases=checkpoint["num_clases"])
    modelo.load_state_dict(checkpoint["state_dict"])
    modelo.eval()
    return modelo


def predecir_jugada(fen: str, ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO) -> str:
    """Predice la jugada más probable según el modelo, entre las jugadas legales de `fen`.

    El modelo da un puntaje por cada una de las 4096 clases posibles
    (`origen*64 + destino`), incluyendo jugadas ilegales para esa posición —
    por eso se evalúa el puntaje solo sobre las jugadas legales, en vez de
    tomar el argmax global.

    Returns:
        La jugada legal de mayor puntaje, en notación SAN.

    Raises:
        ValueError: si la posición no tiene jugadas legales (mate o ahogado).
    """
    tablero = chess.Board(fen)
    jugadas_legales = list(tablero.legal_moves)
    if not jugadas_legales:
        raise ValueError(f"La posición '{fen}' no tiene jugadas legales")

    modelo = cargar_modelo(ruta_checkpoint)
    entrada = tensor_a_entrada_red(board_to_tensor(tablero)).unsqueeze(0)
    with torch.no_grad():
        puntajes = modelo(entrada)[0]

    mejor_jugada = max(
        jugadas_legales,
        key=lambda jugada: puntajes[jugada_a_etiqueta(tablero, jugada)].item(),
    )
    return tablero.san(mejor_jugada)
