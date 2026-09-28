"""Wrapper sobre Stockfish (vía python-chess) para calcular y analizar jugadas."""
from __future__ import annotations

import itertools
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import chess
import chess.engine

from pathlib import Path


def _obtener_ruta_stockfish() -> str:
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path:
        return env_path
    posibles = [
        Path("tools/stockfish/stockfish.exe"),
        Path("tools/stockfish/stockfish"),
        Path(__file__).resolve().parent.parent.parent.parent / "tools" / "stockfish" / "stockfish.exe",
        Path(__file__).resolve().parent.parent.parent.parent / "tools" / "stockfish" / "stockfish",
    ]
    for ruta in posibles:
        if ruta.is_file():
            return str(ruta)
    return "stockfish"


STOCKFISH_PATH = _obtener_ruta_stockfish()

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
    sin abrir el proceso de Stockfish dos veces. Para analizar muchas
    posiciones seguidas conviene `analizar_posiciones`, que no abre un proceso
    por posición.

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
        return _analizar_con_motor(motor, tablero, tiempo_limite, num_variaciones)


def analizar_posiciones(
    fens: list[str],
    nivel: int = 20,
    tiempo_limite: float = 1.0,
    num_variaciones: int = 3,
    max_motores: int | None = None,
) -> list[dict]:
    """Analiza varias posiciones y devuelve lo mismo que
    `[analizar_posicion(f, nivel, tiempo_limite, num_variaciones) for f in fens]`
    (mismo orden, mismo formato de cada resultado), pero mucho más rápido.

    Abrir un proceso de Stockfish cuesta más que el propio análisis de una
    posición corta, así que acá cada motor se abre UNA sola vez y se reutiliza
    para todas las posiciones que le tocan. Las posiciones se reparten entre
    hasta `max_motores` motores que corren en paralelo, cada uno en su propio
    hilo y con el mismo `Skill Level` que `analizar_posicion`; nunca se abren
    más motores que posiciones. Los hilos van tomando la siguiente posición
    libre, así que el trabajo queda parejo aunque algunas tarden más.

    Todos los FEN y el nivel se validan antes de abrir ningún motor. Si un
    análisis falla, el error se propaga igual que en la versión secuencial,
    los demás hilos dejan de tomar posiciones nuevas y todos los motores se
    cierran. Una lista vacía devuelve `[]` sin abrir Stockfish.

    Args:
        fens: posiciones en notación FEN.
        nivel: fuerza de juego de Stockfish (0-20, "Skill Level").
        tiempo_limite: tiempo máximo de cálculo por posición, en segundos.
        num_variaciones: líneas MultiPV por posición.
        max_motores: máximo de procesos de Stockfish simultáneos (>= 1). Si es `None`
            usa `min(4, núcleos de CPU)`: con menos núcleos que motores, cada búsqueda
            por tiempo recibe menos CPU y llega menos profundo.

    Raises:
        ValueError: si `nivel` está fuera de rango, algún FEN es inválido o
            imposible, o `max_motores` es menor a 1.
    """
    if max_motores is None:
        max_motores = min(4, os.cpu_count() or 2)
    if max_motores < 1:
        raise ValueError(f"max_motores debe ser al menos 1, recibido {max_motores}")
    if not fens:
        return []
    _validar_nivel(nivel)
    tableros = [_validar_fen(fen) for fen in fens]

    resultados: list = [None] * len(tableros)
    siguiente_posicion = itertools.count()
    cancelar = threading.Event()

    def analizar_las_que_toquen() -> None:
        try:
            with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as motor:
                motor.configure({"Skill Level": nivel})
                while not cancelar.is_set():
                    indice = next(siguiente_posicion)
                    if indice >= len(tableros):
                        return
                    resultados[indice] = _analizar_con_motor(
                        motor, tableros[indice], tiempo_limite, num_variaciones
                    )
        except BaseException:
            cancelar.set()
            raise

    cantidad_motores = min(max_motores, len(tableros))
    with ThreadPoolExecutor(max_workers=cantidad_motores) as pool:
        trabajos = [pool.submit(analizar_las_que_toquen) for _ in range(cantidad_motores)]
        for trabajo in trabajos:
            trabajo.result()
    return resultados


def _analizar_con_motor(
    motor: chess.engine.SimpleEngine, tablero: chess.Board, tiempo_limite: float, num_variaciones: int
) -> dict:
    """Analiza `tablero` con un motor ya abierto y configurado; arma el dict de `analizar_posicion`."""
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
