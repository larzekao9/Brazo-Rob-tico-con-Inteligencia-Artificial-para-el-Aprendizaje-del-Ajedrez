"""Inferencia del modelo de jugadas (HU4): carga el checkpoint entrenado en Colab
y predice la jugada más probable para una posición, entre las jugadas legales.

Esto nunca decide la jugada real de la partida (ver reglas del PAPs) — Stockfish
sigue siendo la única fuente de la jugada que se ejecuta. Este módulo es la base
para conectar el modelo propio a `EstrategiaJugada` (HU4) y a las explicaciones
de HU5.
"""
from __future__ import annotations

import re
import time
from functools import lru_cache
from pathlib import Path

import chess
import torch
import torch.nn.functional as F

from backend.servicios.aprendizaje.modelo_jugadas import (
    NUM_CLASES,
    RedPrediccionJugadas,
    RedResNetAjedrez,
    RedSEResNetAjedrez,
    tensor_a_entrada_red,
)
from training.data_pipeline import board_to_tensor, jugada_a_etiqueta

RUTA_CHECKPOINT_POR_DEFECTO = Path("training/checkpoints/modelo_jugadas_v1_2026-09-14.pt")


@lru_cache(maxsize=None)
def cargar_modelo(ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO) -> torch.nn.Module:
    """Carga los pesos del checkpoint y devuelve el modelo listo para inferencia.

    Detecta automáticamente si el checkpoint corresponde a la arquitectura
    clásica (v1/v2), ResNet (v3) o SE-ResNet con atención (v4) por metadatos o por sus capas.
    Cachea por ruta de checkpoint para no releer el archivo en cada predicción.
    """
    checkpoint = torch.load(Path(ruta_checkpoint), map_location="cpu")
    num_clases = checkpoint.get("num_clases", NUM_CLASES)
    arquitectura = checkpoint.get("arquitectura", "")
    state_dict = checkpoint["state_dict"]

    if arquitectura == "se_resnet" or any("se.fc" in k for k in state_dict):
        indices = [int(k.split(".")[1]) for k in state_dict if k.startswith("torre_residual.")]
        num_bloques = max(indices) + 1 if indices else 6
        canales = checkpoint.get("canales")
        if canales is None and "entrada.0.weight" in state_dict:
            canales = state_dict["entrada.0.weight"].shape[0]
        if canales is None:
            canales = 128
        modelo = RedSEResNetAjedrez(
            canales=canales,
            cantidad_bloques=num_bloques,
            cantidad_clases=num_clases,
        )
    elif arquitectura == "resnet" or any(k.startswith("torre_residual") for k in state_dict):
        indices = [int(k.split(".")[1]) for k in state_dict if k.startswith("torre_residual.")]
        num_bloques = max(indices) + 1 if indices else 4
        canales = checkpoint.get("canales")
        if canales is None and "entrada.0.weight" in state_dict:
            canales = state_dict["entrada.0.weight"].shape[0]
        if canales is None:
            canales = 128
        modelo = RedResNetAjedrez(
            canales=canales,
            cantidad_bloques=num_bloques,
            cantidad_clases=num_clases,
        )
    else:
        modelo = RedPrediccionJugadas(cantidad_clases=num_clases)

    modelo.load_state_dict(state_dict)
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


def predecir_top_jugadas(
    fen: str, top_n: int = 3, ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO
) -> list[tuple[str, float]]:
    """Predice las `top_n` jugadas más probables con sus probabilidades reales.

    Aplica softmax solo sobre jugadas legales (mismo filtro que `predecir_jugada`),
    devuelve tuplas (SAN, probabilidad).

    Returns:
        Lista de tuplas (jugada_san, probabilidad) ordenada por probabilidad descendente.

    Raises:
        ValueError: si la posición no tiene jugadas legales.
        FileNotFoundError: si no existe el checkpoint.
    """
    inicio = time.perf_counter()
    tablero = chess.Board(fen)
    jugadas_legales = list(tablero.legal_moves)
    if not jugadas_legales:
        raise ValueError(f"La posición '{fen}' no tiene jugadas legales")

    modelo = cargar_modelo(ruta_checkpoint)
    entrada = tensor_a_entrada_red(board_to_tensor(tablero)).unsqueeze(0)

    with torch.no_grad():
        puntajes = modelo(entrada)[0]

    indices = [jugada_a_etiqueta(tablero, jugada) for jugada in jugadas_legales]
    puntajes_legales = puntajes[indices]
    probs = F.softmax(puntajes_legales, dim=0)

    top_k = min(top_n, len(jugadas_legales))
    top_indices = torch.topk(probs, top_k).indices.tolist()

    resultado = [
        (tablero.san(jugadas_legales[i]), probs[i].item())
        for i in top_indices
    ]

    _ = time.perf_counter() - inicio
    return resultado


def calcular_saliencia(
    fen: str, ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO
) -> list[float]:
    """Calcula mapa de saliencia 8x8 (64 valores [0,1]) por gradiente de entrada.

    Gradiente real: `requires_grad_(True)` → forward → `backward()` sobre score
    de la jugada elegida → `input.grad.abs().sum(dim=1)` por casilla → normalizar 0-1.

    Returns:
        Lista de 64 floats en [0,1] representando importancia de cada casilla.

    Raises:
        ValueError: si la posición no tiene jugadas legales.
        FileNotFoundError: si no existe el checkpoint.
    """
    inicio = time.perf_counter()
    tablero = chess.Board(fen)
    jugadas_legales = list(tablero.legal_moves)
    if not jugadas_legales:
        raise ValueError(f"La posición '{fen}' no tiene jugadas legales")

    modelo = cargar_modelo(ruta_checkpoint)

    tensor_posicion = board_to_tensor(tablero)
    entrada = tensor_a_entrada_red(tensor_posicion).unsqueeze(0)
    entrada.requires_grad_(True)

    puntajes = modelo(entrada)[0]

    mejor_jugada = max(
        jugadas_legales,
        key=lambda jugada: puntajes[jugada_a_etiqueta(tablero, jugada)].item(),
    )
    idx_mejor = jugada_a_etiqueta(tablero, mejor_jugada)
    score_mejor = puntajes[idx_mejor]

    modelo.zero_grad()
    score_mejor.backward()

    grad = entrada.grad.abs().sum(dim=1).squeeze(0).detach().cpu().numpy()
    grad_flat = grad.flatten()

    min_val, max_val = grad_flat.min(), grad_flat.max()
    if max_val > min_val:
        saliencia_norm = (grad_flat - min_val) / (max_val - min_val)
    else:
        saliencia_norm = grad_flat * 0.0

    _ = time.perf_counter() - inicio
    return saliencia_norm.tolist()


def estado_modelo(ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO) -> dict:
    """Devuelve metadatos del modelo cargado.

    Parsea versión/fecha del nombre (`modelo_jugadas_v\\d+_\\d{4}-\\d{2}-\\d{2}\\.pt`),
    num_clases del checkpoint, dispositivo real.

    Returns:
        dict con: version (int), fecha_entrenamiento (str), num_clases (int),
        dispositivo (str), latencia_ms (float).

    Raises:
        FileNotFoundError: si no existe el checkpoint.
    """
    inicio = time.perf_counter()
    path = Path(ruta_checkpoint)
    checkpoint = torch.load(path, map_location="cpu")

    match = re.search(r"modelo_jugadas_v(\d+)_(\d{4}-\d{2}-\d{2})\.pt", path.name)
    if match:
        version = int(match.group(1))
        fecha_entrenamiento = match.group(2)
    else:
        version = 0
        fecha_entrenamiento = "desconocida"

    num_clases = checkpoint.get("num_clases", 4096)

    if torch.cuda.is_available():
        dispositivo = torch.cuda.get_device_name(0)
    else:
        dispositivo = "cpu"

    latencia_ms = (time.perf_counter() - inicio) * 1000

    return {
        "version": version,
        "fecha_entrenamiento": fecha_entrenamiento,
        "num_clases": num_clases,
        "dispositivo": dispositivo,
        "latencia_ms": latencia_ms,
    }
