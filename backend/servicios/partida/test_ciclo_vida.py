from datetime import datetime, timedelta, timezone

import chess
import pytest

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidasEnMemoria
from backend.servicios.calibracion import MIN_JUGADAS_PARTIDA_VALIDA
from backend.servicios.partida.ciclo_vida import (
    HORAS_INACTIVIDAD_ABANDONO,
    MINUTOS_PARTIDA_VACIA,
    cerrar_partidas_pendientes,
    limpiar_partidas_inactivas,
    partida_en_curso_de,
)

_RUY_LOPEZ_HASTA_ENROQUE = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7"]
"""Diez plies (5 del jugador) siempre legales, sin pasar por Stockfish — deja
`jugadas_jugador == MIN_JUGADAS_PARTIDA_VALIDA` exacto."""


def _hace(minutos: int = 0, horas: int = 0) -> str:
    momento = datetime.now(timezone.utc) - timedelta(minutes=minutos, hours=horas)
    return momento.isoformat()


def _partida_con_jugadas(cantidad_plies: int, usuario_id: int = 1) -> Partida:
    tablero = chess.Board()
    for jugada_san in _RUY_LOPEZ_HASTA_ENROQUE[:cantidad_plies]:
        tablero.push_san(jugada_san)
    return Partida(tablero=tablero, nivel=5, usuario_id=usuario_id)


def test_limpiar_partidas_inactivas_borra_partida_vacia_vieja() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = Partida(nivel=5, usuario_id=1)
    partida.creada_en = _hace(minutos=MINUTOS_PARTIDA_VACIA + 5)
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    with pytest.raises(KeyError):
        repositorio.obtener(partida.id)


def test_limpiar_partidas_inactivas_conserva_partida_vacia_reciente() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = Partida(nivel=5, usuario_id=1)
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    assert repositorio.obtener(partida.id).estado == "en_curso"


def test_limpiar_partidas_inactivas_borra_partida_con_pocas_jugadas_inactiva() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida_con_jugadas(2)  # 1 jugada del jugador, menos que el mínimo
    partida.actualizada_en = _hace(horas=HORAS_INACTIVIDAD_ABANDONO + 1)
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    with pytest.raises(KeyError):
        repositorio.obtener(partida.id)


def test_limpiar_partidas_inactivas_abandona_partida_con_jugadas_suficientes_inactiva() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida_con_jugadas(2 * MIN_JUGADAS_PARTIDA_VALIDA)
    partida.actualizada_en = _hace(horas=HORAS_INACTIVIDAD_ABANDONO + 1)
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    assert repositorio.obtener(partida.id).estado == "abandonada"


def test_limpiar_partidas_inactivas_conserva_partida_activa_reciente() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida_con_jugadas(2)
    partida.actualizada_en = _hace(minutos=5)
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    assert repositorio.obtener(partida.id).estado == "en_curso"


def test_limpiar_partidas_inactivas_nunca_toca_una_demostracion() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = Partida(nivel=5, usuario_id=1, es_demostracion=True)
    partida.creada_en = _hace(minutos=MINUTOS_PARTIDA_VACIA + 100)
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    partida_tras_barrido = repositorio.obtener(partida.id)
    assert partida_tras_barrido.estado == "en_curso"
    assert partida_tras_barrido.es_demostracion is True


def test_cerrar_partidas_pendientes_usa_fecha_naive_como_utc() -> None:
    # Una partida releída de Postgres puede traer `creada_en` sin offset de
    # zona (columna TIMESTAMP sin zona) — tiene que tratarse como UTC, no
    # como si nunca hubiera pasado el tiempo.
    repositorio = RepositorioPartidasEnMemoria()
    partida = Partida(nivel=5, usuario_id=1)
    momento_naive = (datetime.now(timezone.utc) - timedelta(minutes=MINUTOS_PARTIDA_VACIA + 5)).replace(tzinfo=None)
    partida.creada_en = momento_naive.isoformat()
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    with pytest.raises(KeyError):
        repositorio.obtener(partida.id)


def test_cerrar_partidas_pendientes_solo_afecta_al_usuario_indicado() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    de_otro = Partida(nivel=5, usuario_id=2)
    repositorio.guardar(de_otro)
    del_usuario = Partida(nivel=5, usuario_id=1)
    repositorio.guardar(del_usuario)

    cerrar_partidas_pendientes(repositorio, 1)

    assert repositorio.obtener(de_otro.id).estado == "en_curso"
    with pytest.raises(KeyError):
        repositorio.obtener(del_usuario.id)


def test_partida_en_curso_de_ninguna_si_no_hay_partidas() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    assert partida_en_curso_de(repositorio, 1) is None


def test_partida_en_curso_de_ninguna_si_lleva_demasiado_inactiva() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida_con_jugadas(2, usuario_id=1)
    partida.actualizada_en = _hace(horas=HORAS_INACTIVIDAD_ABANDONO + 1)
    repositorio.guardar(partida)

    assert partida_en_curso_de(repositorio, 1) is None


def test_partida_en_curso_de_devuelve_la_activa_con_jugadas() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida_con_jugadas(2, usuario_id=1)
    partida.actualizada_en = _hace(minutos=5)
    repositorio.guardar(partida)

    encontrada = partida_en_curso_de(repositorio, 1)

    assert encontrada is not None
    assert encontrada.id == partida.id
