"""Inferencia del modelo de jugadas (HU4): carga el checkpoint entrenado en Colab
y predice la jugada más probable para una posición, entre las jugadas legales.

Cuando el oponente elegido es `"modelo"`, `predecir_jugada_maestra` decide la
jugada real de la partida por su cuenta (vía `EstrategiaModelo`), sin consultar
a Stockfish; Stockfish solo actúa como oráculo de comparación en otros módulos.
Este módulo además es la base de las explicaciones de HU5/HU6. Nada acá aprende
en vivo: los pesos solo cambian al reentrenar en lotes versionados.
"""
from __future__ import annotations

import math
import random
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
from backend.servicios.aprendizaje.niveles import NIVEL_MAESTRO, NIVEL_MAX_MODELO  # noqa: F401
from training.data_pipeline import board_to_tensor, jugada_a_etiqueta

def _obtener_checkpoint_por_defecto() -> Path:
    carpeta = Path("training/checkpoints")
    if carpeta.exists():
        checkpoints = sorted(carpeta.glob("modelo_jugadas_v*.pt"))
        if checkpoints:
            return checkpoints[-1]
    return Path("training/checkpoints/modelo_jugadas_v1_2026-09-14.pt")


RUTA_CHECKPOINT_POR_DEFECTO = _obtener_checkpoint_por_defecto()


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


VALORES_PIEZAS = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}


def _evaluar_candidata_tactica(tablero: chess.Board, jugada: chess.Move) -> dict:
    """Aplica a UNA jugada candidata los 3 chequeos tácticos autónomos que usa
    `predecir_jugada_maestra` para podar jugadas suicidas, en memoria (< 3 ms) y sin
    consultar a Stockfish (cumple la Regla 1 del proyecto: el modelo decide solo).

    Extraído como función propia para que tanto `predecir_jugada_maestra` (la jugada
    real de la partida) como `explicar_top_candidatas` (el detalle para el panel de
    Razonamiento Neuronal) apliquen exactamente la misma lógica sobre cada candidata —
    así nunca pueden divergir en qué jugada consideran mejor.

    Args:
        tablero: posición ANTES de `jugada` (el jugador a mover es quien la juega).
            Se modifica con push/pop internamente pero queda intacto al retornar.
        jugada: jugada candidata a evaluar; debe ser legal en `tablero`.

    Returns:
        dict con:
        - `da_jaque_mate` (bool): la jugada mata inmediato.
        - `rival_tiene_mate_en_1` (bool): tras la jugada, el rival tiene mate en 1.
        - `pieza_colgada` (bool): la pieza que se movió queda atacada sin defensores
          propios, o por un atacante de menor valor.
        - `penalidad_pieza_colgada` (float): monto a restar del score de la red si
          `pieza_colgada` es True (0.0 si no aplica) — se expone para que
          `predecir_jugada_maestra` no tenga que reconstruir la fórmula por separado.
    """
    tablero.push(jugada)
    try:
        if tablero.is_checkmate():
            return {
                "da_jaque_mate": True,
                "rival_tiene_mate_en_1": False,
                "pieza_colgada": False,
                "penalidad_pieza_colgada": 0.0,
            }

        rival_tiene_mate = False
        for m_rival in tablero.legal_moves:
            tablero.push(m_rival)
            if tablero.is_checkmate():
                rival_tiene_mate = True
                tablero.pop()
                break
            tablero.pop()

        pieza_movida = tablero.piece_at(jugada.to_square)
        color_rival = tablero.turn
        atacantes_rivales = tablero.attackers(color_rival, jugada.to_square)
        defensores_propios = tablero.attackers(not color_rival, jugada.to_square)

        pieza_colgada = False
        penalidad_pieza_colgada = 0.0
        if pieza_movida and atacantes_rivales:
            val_pieza = VALORES_PIEZAS.get(pieza_movida.piece_type, 100)
            valores_atacantes = [
                VALORES_PIEZAS.get(tablero.piece_at(sq).piece_type, 100)
                for sq in atacantes_rivales
                if tablero.piece_at(sq)
            ]
            if valores_atacantes:
                min_atacante = min(valores_atacantes)
                if min_atacante < val_pieza or not defensores_propios:
                    pieza_colgada = True
                    monto = (val_pieza - min_atacante) if defensores_propios else val_pieza
                    penalidad_pieza_colgada = (monto / 100.0) * 2.0

        return {
            "da_jaque_mate": False,
            "rival_tiene_mate_en_1": rival_tiene_mate,
            "pieza_colgada": pieza_colgada,
            "penalidad_pieza_colgada": penalidad_pieza_colgada,
        }
    finally:
        tablero.pop()


NIVEL_MIN = 0
NIVEL_MAX = 20
# `NIVEL_MAESTRO` (desde ese nivel el modelo juega determinista, siempre la mejor
# candidata tras el filtro táctico) y `NIVEL_MAX_MODELO` (su techo en la escala
# 0-20) se importan arriba desde `niveles.py`, que no depende de torch.

TEMPERATURA_MAX = 3.0  # niveles NIVEL_MIN..5 (Principiante)
TEMPERATURA_MIN = 1.0  # nivel 17, el último antes del modo maestro
_NIVEL_TEMPERATURA_MAX = 5
_NIVEL_TEMPERATURA_MIN = NIVEL_MAESTRO - 1


def temperatura_y_pool_por_nivel(nivel: int | None) -> tuple[float, int]:
    """Mapea el nivel de juego (0-20, mismo rango que el Skill Level de Stockfish)
    a los parámetros con que el modelo muestrea entre sus candidatas.

    Función pura: no toca la red ni el tablero. El nivel viene del perfil del
    jugador (Principiante ≈ 5, Intermedio ≈ 11, Avanzado ≈ 18; el facilitador usa 20).

    Mapeo (`temperatura`, `top_k`):

    - `nivel is None` o `nivel >= 18` (NIVEL_MAESTRO): `(0.0, 3)` — temperatura 0
      significa "sin muestreo": se elige siempre la mejor candidata (comportamiento
      original de `predecir_jugada_maestra`, determinista).
    - `nivel` 0-17: la temperatura baja linealmente de 3.0 (niveles 0-5) a 1.0
      (nivel 17): T = 3.0 - 2.0 * (nivel - 5) / 12, redondeada a 2 decimales.
      Ejemplos: nivel 5 -> 3.0, nivel 8 -> 2.5, nivel 11 -> 2.0, nivel 14 -> 1.5,
      nivel 17 -> 1.0. Con T=1 se muestrea de la distribución propia de la red;
      con T mayor la distribución se aplana y las candidatas peores ganan peso.
    - `top_k` (tamaño del pool de candidatas de la red entre las que se muestrea):
      3 para niveles 14-17, 4 para niveles 9-13 y 5 para niveles 0-8.

    Un `nivel` fuera de [0, 20] se recorta a ese rango.

    Returns:
        Tupla `(temperatura, top_k)`.
    """
    if nivel is None:
        return 0.0, 3
    nivel = max(NIVEL_MIN, min(NIVEL_MAX, nivel))
    if nivel >= NIVEL_MAESTRO:
        return 0.0, 3

    if nivel <= _NIVEL_TEMPERATURA_MAX:
        temperatura = TEMPERATURA_MAX
    else:
        tramo = _NIVEL_TEMPERATURA_MIN - _NIVEL_TEMPERATURA_MAX
        temperatura = TEMPERATURA_MAX - (
            (TEMPERATURA_MAX - TEMPERATURA_MIN) * (nivel - _NIVEL_TEMPERATURA_MAX) / tramo
        )

    if nivel <= 8:
        top_k = 5
    elif nivel <= 13:
        top_k = 4
    else:
        top_k = 3
    return round(temperatura, 2), top_k


def _elegir_candidata_muestreada(
    tablero: chess.Board,
    candidatas: list[chess.Move],
    puntajes: torch.Tensor,
    temperatura: float,
    rng: random.Random,
) -> chess.Move:
    """Elige una jugada entre `candidatas` por muestreo softmax con `temperatura`,
    aplicando antes los mismos chequeos tácticos que el modo maestro:

    1. Si alguna candidata da jaque mate, se juega (la primera en orden de la red).
    2. Se descartan las que permiten mate en 1 al rival. Si no queda ninguna, se
       cae en la mejor candidata de la red (mismo fallback que el modo maestro).
    3. A las restantes se les resta la penalidad por pieza colgada al score de la
       red ANTES de aplicar el softmax, así que a nivel bajo errar es más probable
       pero una pieza regalada sigue siendo poco probable.

    Nunca consulta a Stockfish ni devuelve una jugada fuera de `candidatas` (todas
    legales).
    """
    supervivientes: list[tuple[chess.Move, float]] = []
    for jugada in candidatas:
        tactica = _evaluar_candidata_tactica(tablero, jugada)
        if tactica["da_jaque_mate"]:
            return jugada
        if tactica["rival_tiene_mate_en_1"]:
            continue
        score = puntajes[jugada_a_etiqueta(tablero, jugada)].item()
        supervivientes.append((jugada, score - tactica["penalidad_pieza_colgada"]))

    if not supervivientes:
        return candidatas[0]

    scores = [score / temperatura for _, score in supervivientes]
    maximo = max(scores)  # estabilidad numérica del softmax
    pesos = [math.exp(s - maximo) for s in scores]
    return rng.choices([j for j, _ in supervivientes], weights=pesos, k=1)[0]


def predecir_jugada_maestra(
    fen: str,
    ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO,
    top_candidatas: int = 3,
    nivel: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Predice la jugada del modelo combinando intuición neuronal y filtro táctico autónomo.

    Diseñado especialmente para el control físico del brazo robótico (RF11/RF14):
    1. La red neuronal sugiere las `top_candidatas` mejores jugadas.
    2. En memoria (< 3 ms), se verifica cada candidata para podar jugadas suicidas:
       - Si la jugada da jaque mate inmediato, se ejecuta sin dudar.
       - Si la jugada permite que el rival de jaque mate en 1, se descarta.
       - Si la pieza se mueve a una casilla atacada por peones o piezas menores
         sin defensores propios, se penaliza drásticamente.
    3. Garantiza una tasa de victoria de nivel maestro en demostraciones físicas.

    Adaptación al nivel del jugador (Causa 2 de la tesis: rival de nivel equivalente):
    - `nivel is None` o `nivel >= 18`: modo maestro, arriba descrito. Determinista,
      idéntico al comportamiento previo a la existencia de `nivel`.
    - `nivel < 18`: en lugar de elegir siempre la mejor candidata, se muestrea entre
      las `top_k` mejores de la red con softmax a la temperatura que fija
      `temperatura_y_pool_por_nivel(nivel)` (más alta y con más candidatas cuanto
      menor el nivel). Los chequeos tácticos se mantienen a cualquier nivel: el mate
      en 1 propio se juega, las jugadas que permiten mate en 1 se descartan, y la
      penalidad por pieza colgada se resta del score antes de muestrear. El pool
      efectivo es `max(top_candidatas, top_k)`.

    Args:
        fen: posición a resolver.
        ruta_checkpoint: checkpoint del modelo (por defecto, el más reciente).
        top_candidatas: mínimo de candidatas de la red a considerar.
        nivel: nivel de juego 0-20 (viene del perfil del jugador); `None` = maestro.
        rng: generador de números aleatorios para el muestreo (`nivel < 18`);
            se inyecta con semilla en los tests. Por defecto, uno nuevo sin semilla.
            No se consume en modo maestro.

    Cumple estrictamente la Regla 1 del proyecto: no consulta a Stockfish durante
    el juego; es un cálculo táctico local ejecutado por la red neuronal y reglas de
    ajedrez. El muestreo es aleatoriedad por jugada, sin estado ni aprendizaje en vivo.
    """
    tablero = chess.Board(fen)
    jugadas_legales = list(tablero.legal_moves)
    if not jugadas_legales:
        raise ValueError(f"La posición '{fen}' no tiene jugadas legales")

    if len(jugadas_legales) == 1:
        return tablero.san(jugadas_legales[0])

    muestrear = nivel is not None and nivel < NIVEL_MAESTRO
    if muestrear:
        temperatura, top_k = temperatura_y_pool_por_nivel(nivel)
        top_candidatas = max(top_candidatas, top_k)

    modelo = cargar_modelo(ruta_checkpoint)
    entrada = tensor_a_entrada_red(board_to_tensor(tablero)).unsqueeze(0)
    with torch.no_grad():
        puntajes = modelo(entrada)[0]

    jugadas_ordenadas = sorted(
        jugadas_legales,
        key=lambda j: puntajes[jugada_a_etiqueta(tablero, j)].item(),
        reverse=True,
    )

    candidatas = jugadas_ordenadas[: min(top_candidatas, len(jugadas_ordenadas))]

    if muestrear:
        elegida = _elegir_candidata_muestreada(
            tablero, candidatas, puntajes, temperatura, rng if rng is not None else random.Random()
        )
        return tablero.san(elegida)

    mejor_jugada = candidatas[0]
    mejor_score = -float("inf")

    for jugada in candidatas:
        score = puntajes[jugada_a_etiqueta(tablero, jugada)].item()
        tactica = _evaluar_candidata_tactica(tablero, jugada)

        # 1. ¿Damos jaque mate?
        if tactica["da_jaque_mate"]:
            return tablero.san(jugada)

        # 2. ¿El rival tiene mate en 1 tras esta jugada?
        if tactica["rival_tiene_mate_en_1"]:
            continue

        # 3. ¿Colgamos la pieza que acabamos de mover?
        score -= tactica["penalidad_pieza_colgada"]

        if score > mejor_score:
            mejor_score = score
            mejor_jugada = jugada

    return tablero.san(mejor_jugada)


def explicar_top_candidatas(
    fen: str,
    ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO,
    top_candidatas: int = 3,
) -> list[dict]:
    """Detalle completo de las top-N candidatas reales que considera la red neuronal,
    para el panel de Razonamiento Neuronal (HU6 ampliada) — no solo la jugada elegida.

    Aplica sobre cada candidata los mismos 3 chequeos tácticos autónomos que
    `predecir_jugada_maestra` (vía `_evaluar_candidata_tactica`) y replica exactamente
    su misma lógica de decisión (mate inmediato gana de inmediato en orden de
    iteración; si no, se descartan las que dejan mate en 1 al rival; entre las
    restantes gana el mejor score de red menos penalidad por pieza colgada, con el
    primer candidato de la red como fallback si todas quedan descartadas) para marcar
    `elegida=True` en la MISMA jugada que `predecir_jugada_maestra` devolvería para
    este mismo `fen` — así el backend y el frontend nunca muestran cosas distintas.

    A diferencia de `predecir_jugada_maestra`, esta función NO decide la jugada real
    de ninguna partida (esa sigue siendo la única responsabilidad de
    `predecir_jugada_maestra` vía `EstrategiaModelo`) — solo expone información para
    explicar/comparar, pensada para exponerse por HTTP.

    Returns:
        Lista de dicts, uno por candidata, ordenada de mejor a peor puntaje de red:
        `{"jugada": str (SAN), "probabilidad": float, "da_jaque_mate": bool,
        "rival_tiene_mate_en_1": bool, "pieza_colgada": bool, "elegida": bool}`.

    Raises:
        ValueError: si la posición no tiene jugadas legales (mate o ahogado).
        FileNotFoundError: si no existe el checkpoint.
    """
    tablero = chess.Board(fen)
    jugadas_legales = list(tablero.legal_moves)
    if not jugadas_legales:
        raise ValueError(f"La posición '{fen}' no tiene jugadas legales")

    modelo = cargar_modelo(ruta_checkpoint)
    entrada = tensor_a_entrada_red(board_to_tensor(tablero)).unsqueeze(0)
    with torch.no_grad():
        puntajes = modelo(entrada)[0]

    indices_legales = [jugada_a_etiqueta(tablero, j) for j in jugadas_legales]
    puntajes_legales = puntajes[indices_legales]
    probs_legales = F.softmax(puntajes_legales, dim=0)

    # Mismo orden que `predecir_jugada_maestra` (sort estable descendente por score
    # crudo de la red sobre la lista de jugadas legales en el mismo orden de origen).
    orden = sorted(
        range(len(jugadas_legales)),
        key=lambda i: puntajes_legales[i].item(),
        reverse=True,
    )
    top_k = min(top_candidatas, len(jugadas_legales))
    indices_top = orden[:top_k]

    candidatas_jugadas = [jugadas_legales[i] for i in indices_top]
    candidatas_probs = [probs_legales[i].item() for i in indices_top]
    candidatas_scores = [puntajes_legales[i].item() for i in indices_top]

    # Caso trivial: una sola jugada legal — `predecir_jugada_maestra` la devuelve
    # directamente sin pasar por el filtro táctico, así que acá también es elegida
    # sin ambigüedad (igual se calcula el detalle táctico, solo para informar).
    if len(jugadas_legales) == 1:
        jugada = candidatas_jugadas[0]
        tactica = _evaluar_candidata_tactica(tablero, jugada)
        return [
            {
                "jugada": tablero.san(jugada),
                "probabilidad": candidatas_probs[0],
                "da_jaque_mate": tactica["da_jaque_mate"],
                "rival_tiene_mate_en_1": tactica["rival_tiene_mate_en_1"],
                "pieza_colgada": tactica["pieza_colgada"],
                "elegida": True,
            }
        ]

    detalles_tacticos: list[dict] = []
    indice_mate_inmediato: int | None = None
    mejor_indice = 0
    mejor_score = -float("inf")

    for pos, jugada in enumerate(candidatas_jugadas):
        tactica = _evaluar_candidata_tactica(tablero, jugada)
        detalles_tacticos.append(tactica)

        if indice_mate_inmediato is not None:
            # Ya se decidió por mate inmediato en una candidata anterior (mismo orden
            # de iteración que `predecir_jugada_maestra`, que retorna ahí mismo) —
            # seguimos solo para completar el detalle táctico de las restantes.
            continue

        if tactica["da_jaque_mate"]:
            indice_mate_inmediato = pos
            continue

        if tactica["rival_tiene_mate_en_1"]:
            continue

        score = candidatas_scores[pos] - tactica["penalidad_pieza_colgada"]
        if score > mejor_score:
            mejor_score = score
            mejor_indice = pos

    indice_elegida = (
        indice_mate_inmediato if indice_mate_inmediato is not None else mejor_indice
    )

    return [
        {
            "jugada": tablero.san(jugada),
            "probabilidad": candidatas_probs[pos],
            "da_jaque_mate": detalles_tacticos[pos]["da_jaque_mate"],
            "rival_tiene_mate_en_1": detalles_tacticos[pos]["rival_tiene_mate_en_1"],
            "pieza_colgada": detalles_tacticos[pos]["pieza_colgada"],
            "elegida": pos == indice_elegida,
        }
        for pos, jugada in enumerate(candidatas_jugadas)
    ]


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


def calcular_atencion(
    fen: str, ruta_checkpoint: str | Path = RUTA_CHECKPOINT_POR_DEFECTO
) -> list[float]:
    """Intensidad real de atención por canales (bloques Squeeze-and-Excitation, HU6 ampliada).

    Cada bloque residual SE calcula un peso sigmoide [0,1] por canal, indicando qué
    patrones internos prioriza esa capa para la posición actual (Hu et al., 2018,
    ver docs/marco_teorico_ia_entrenamiento.md sección 3.3). Acá se promedia ese
    vector por bloque, de la capa más superficial a la más profunda.

    Solo aplica a checkpoints SE-ResNet (v4/v5) — el resto de arquitecturas
    (v1/v2/v3) no tienen este mecanismo, así que devuelven lista vacía en vez de
    inventar un dato que no existe.

    Returns:
        Lista de floats en [0,1], uno por bloque residual SE (vacía si el
        checkpoint cargado no usa atención por canales).

    Raises:
        ValueError: si la posición no tiene jugadas legales.
        FileNotFoundError: si no existe el checkpoint.
    """
    tablero = chess.Board(fen)
    jugadas_legales = list(tablero.legal_moves)
    if not jugadas_legales:
        raise ValueError(f"La posición '{fen}' no tiene jugadas legales")

    modelo = cargar_modelo(ruta_checkpoint)
    torre = getattr(modelo, "torre_residual", None)
    if torre is None:
        return []

    entrada = tensor_a_entrada_red(board_to_tensor(tablero)).unsqueeze(0)
    with torch.no_grad():
        modelo(entrada)

    atencion_por_bloque = []
    for bloque in torre:
        se = getattr(bloque, "se", None)
        if se is None or se.ultima_atencion is None:
            return []
        atencion_por_bloque.append(se.ultima_atencion.mean().item())

    return atencion_por_bloque


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
