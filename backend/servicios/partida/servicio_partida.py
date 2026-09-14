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

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidas, crear_repositorio_partidas
from backend.servicios.estrategias.fabrica_estrategias import TIPOS_SOPORTADOS, crear_estrategia_jugada

_repositorio: RepositorioPartidas = crear_repositorio_partidas()


def crear_partida(nivel: int = 20, tipo_oponente: str = "motor") -> Partida:
    """Crea una partida nueva con el tablero en la posición inicial.

    Raises:
        ValueError: si `tipo_oponente` no es un tipo soportado todavía (ver
            `fabrica_estrategias.TIPOS_SOPORTADOS`) — se valida acá, al crear
            la partida, para no dejar que falle recién en la primera jugada.
    """
    if tipo_oponente not in TIPOS_SOPORTADOS:
        raise ValueError(
            f"Tipo de oponente '{tipo_oponente}' no soportado todavía "
            f"(disponibles: {sorted(TIPOS_SOPORTADOS)})"
        )
    partida = Partida(nivel=nivel, tipo_oponente=tipo_oponente)
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
