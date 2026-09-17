"""Orquesta partidas jugables: aplica la jugada humana y responde con la
estrategia de jugada activa.

Las partidas viven detrás de `RepositorioPartidas` (patrón Repository, sección
4.3) — en memoria del proceso por defecto, o en Postgres si `DATABASE_URL`
está seteada (`crear_repositorio_partidas`, sección 7). Quién decide la
jugada de respuesta es la estrategia que devuelva `crear_estrategia_jugada`
— hoy siempre Stockfish, mañana también el modelo propio o un jugador
humano, sin tocar este archivo (ver PLAN_IMPLEMENTACION_COMPLETO.md,
secciones 4.1 y 4.3).
"""
from __future__ import annotations

import chess

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidas, crear_repositorio_partidas
from backend.servicios.estrategias.fabrica_estrategias import TIPOS_SOPORTADOS, crear_estrategia_jugada
from backend.servicios.motor.motor_ajedrez import analizar_posicion
from backend.servicios.vision.camara import capturar_foto_tablero
from backend.servicios.vision.deteccion_movimiento import detectar_jugada
from backend.servicios.vision.reconocimiento import reconocer_tablero

_repositorio: RepositorioPartidas = crear_repositorio_partidas()


def crear_partida(nivel: int = 20, tipo_oponente: str = "motor", fen_inicial: str | None = None) -> Partida:
    """Crea una partida nueva.

    Por defecto arranca en la posición inicial estándar. Si se pasa
    `fen_inicial` (por ejemplo, el FEN que devolvió `POST /vision/reconocer`
    al escanear un tablero físico), la partida arranca ahí en cambio — así
    se puede seguir jugando digitalmente una posición que se armó sobre un
    tablero real.

    Raises:
        ValueError: si `tipo_oponente` no es un tipo soportado todavía (ver
            `fabrica_estrategias.TIPOS_SOPORTADOS`), o si `fen_inicial` no es
            un FEN válido — ambos se validan acá, al crear la partida, para
            no dejar que fallen recién en la primera jugada.
    """
    if tipo_oponente not in TIPOS_SOPORTADOS:
        raise ValueError(
            f"Tipo de oponente '{tipo_oponente}' no soportado todavía "
            f"(disponibles: {sorted(TIPOS_SOPORTADOS)})"
        )
    if fen_inicial is None:
        partida = Partida(nivel=nivel, tipo_oponente=tipo_oponente)
    else:
        try:
            tablero = chess.Board(fen_inicial)
        except ValueError as error:
            raise ValueError(f"FEN inicial inválido: {fen_inicial}") from error
        if not tablero.is_valid():
            # Puede pasar con una posición mal reconocida por visión (ej.
            # demasiadas piezas) — sintácticamente es un FEN válido, pero
            # Stockfish se cae si se lo pasamos igual (ver motor_ajedrez.py).
            raise ValueError(
                f"La posición reconocida no es válida (imposible en una partida real): {fen_inicial}"
            )
        partida = Partida(tablero=tablero, nivel=nivel, tipo_oponente=tipo_oponente, fen_inicial=fen_inicial)
    _repositorio.guardar(partida)
    return partida


def obtener_partida(partida_id: str) -> Partida:
    """Busca una partida por id.

    Raises:
        KeyError: si no existe una partida con ese id.
    """
    return _repositorio.obtener(partida_id)


def listar_partidas() -> list[Partida]:
    """Devuelve todas las partidas jugadas mientras este proceso está corriendo.

    Es un registro real (HU8/HU11) mientras el backend sigue arriba — no
    sobrevive un reinicio, porque `RepositorioPartidasEnMemoria` no persiste
    a disco. Ver sección 4.3 y 7 de PLAN_IMPLEMENTACION_COMPLETO.md.
    """
    return _repositorio.listar()


def jugadas_legales_desde(partida_id: str, casilla: str) -> list[str]:
    """Devuelve las casillas destino a las que se puede mover la pieza parada en `casilla`.

    Sirve para resaltar en el tablero del frontend las jugadas válidas al
    seleccionar una pieza (HU3) — usa el tablero real de la partida, nunca
    Stockfish, así que no hace falta tener el motor corriendo.

    Raises:
        KeyError: si no existe una partida con ese id.
        ValueError: si `casilla` no es una casilla válida (ej. "e2").
    """
    partida = obtener_partida(partida_id)
    try:
        origen = chess.parse_square(casilla)
    except ValueError as error:
        raise ValueError(f"Casilla inválida: {casilla}") from error
    destinos = {
        chess.square_name(jugada.to_square)
        for jugada in partida.tablero.legal_moves
        if jugada.from_square == origen
    }
    return sorted(destinos)


def mover(partida_id: str, jugada_uci: str) -> dict:
    """Aplica la jugada del humano (UCI) y responde con la jugada de la estrategia activa.

    Raises:
        KeyError: si no existe una partida con ese id.
        ValueError: si la partida ya terminó o la jugada es inválida/ilegal.
    """
    partida = obtener_partida(partida_id)
    if partida.terminada:
        raise ValueError("La partida ya terminó")

    try:
        jugada_humano = partida.tablero.parse_uci(jugada_uci)
    except ValueError as error:
        raise ValueError(f"Jugada inválida: {jugada_uci}") from error
    partida.tablero.push(jugada_humano)

    jugada_motor_san = None
    if not partida.terminada:
        estrategia = crear_estrategia_jugada(partida.tipo_oponente, nivel=partida.nivel)
        jugada_motor_san = estrategia.decidir_jugada(partida.fen)
        partida.tablero.push_san(jugada_motor_san)

    return {
        "fen": partida.fen,
        "jugada_motor": jugada_motor_san,
        "terminada": partida.terminada,
        "resultado": partida.resultado,
        "jugadas": partida.jugadas_san,
    }


def mover_desde_foto(partida_id: str) -> dict:
    """Detecta la jugada hecha en el tablero físico (RF11) y la aplica igual que `mover()`.

    Flujo: (1) el FEN actual de la partida es la posición "antes"; (2) saca
    una foto nueva de la cámara fija; (3) la reconoce a FEN ("después");
    (4) `detectar_jugada` prueba todas las jugadas legales desde "antes" y
    devuelve cuál reproduce "después" exactamente; (5) se aplica con la
    misma lógica que una jugada hecha a clics (incluida la respuesta de la
    estrategia activa).

    Raises:
        KeyError: si no existe una partida con ese id.
        RuntimeError: si no se pudo capturar la foto (cámara).
        FileNotFoundError: si falta el checkpoint del clasificador de piezas.
        ValueError: si la partida ya terminó, si no se reconoció un tablero
            válido en la foto, o si ninguna jugada legal explica el cambio
            entre "antes" y "después" (ej. se movió más de una pieza, o la
            foto se sacó a mitad del movimiento).
    """
    partida = obtener_partida(partida_id)
    if partida.terminada:
        raise ValueError("La partida ya terminó")

    fen_antes = partida.fen
    tablero_antes = chess.Board(fen_antes)
    turno_despues = "b" if tablero_antes.turn == chess.WHITE else "w"

    imagen = capturar_foto_tablero()
    fen_despues = reconocer_tablero(imagen, turno=turno_despues)

    jugada_san = detectar_jugada(fen_antes, fen_despues)
    if jugada_san is None:
        raise ValueError(
            "No se pudo determinar qué jugada se hizo — la foto no coincide "
            "con ninguna jugada legal desde la posición anterior"
        )
    jugada_uci = tablero_antes.parse_san(jugada_san).uci()
    return mover(partida_id, jugada_uci)


def analisis_completo(partida_id: str, tiempo_limite: float = 0.3) -> dict:
    """Analiza con Stockfish cada jugada ya jugada de una partida (vista de aprendizaje, HU5/HU6).

    Reconstruye, jugada por jugada, todas las posiciones por las que pasó la
    partida desde `fen_inicial`, y le pide a `analizar_posicion` la evaluación
    de cada una. `analizar_posicion` siempre evalúa desde el punto de vista de
    quien tiene el turno en ese FEN — la posición "después" de una jugada le
    toca mover al rival, así que su evaluación queda en la perspectiva del
    rival, y hay que negarla para volver a la perspectiva de quien jugó, y así
    poder compararla contra lo que hubiera valido la mejor jugada (calculada
    en la posición "antes", ya en esa misma perspectiva).

    Abre un proceso de Stockfish por cada posición (N+1 para N jugadas), así
    que es lento para partidas largas — es una acción explícita del usuario
    ("analizar esta partida"), no algo que corra automáticamente, y
    `tiempo_limite` por defecto es más bajo que en el resto del motor para
    no tardar demasiado.

    Raises:
        KeyError: si no existe una partida con ese id.
    """
    partida = obtener_partida(partida_id)

    tablero = chess.Board(partida.fen_inicial)
    posiciones_fen = [tablero.fen()]
    for jugada in partida.tablero.move_stack:
        tablero.push(jugada)
        posiciones_fen.append(tablero.fen())

    analisis_por_posicion = [
        analizar_posicion(fen, partida.nivel, tiempo_limite) for fen in posiciones_fen
    ]

    resultado = []
    for i, jugada_san in enumerate(partida.jugadas_san):
        antes = analisis_por_posicion[i]
        despues = analisis_por_posicion[i + 1]

        eval_resultante_cp = None if despues["evaluacion_cp"] is None else -despues["evaluacion_cp"]
        mate_resultante = None if despues["mate_en"] is None else -despues["mate_en"]

        resultado.append({
            "numero_ply": i + 1,
            "color": "blanco" if i % 2 == 0 else "negro",
            "jugada_san": jugada_san,
            "fen_antes": posiciones_fen[i],
            "fen_despues": posiciones_fen[i + 1],
            "evaluacion_cp": eval_resultante_cp,
            "mate_en": mate_resultante,
            "mejor_jugada_motor": antes["jugada"],
            "evaluacion_mejor_cp": antes["evaluacion_cp"],
            "mate_en_mejor": antes["mate_en"],
            "variantes_candidatas": antes["variantes_candidatas"],
        })

    return {"partida_id": partida_id, "jugadas": resultado}
