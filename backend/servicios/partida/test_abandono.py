"""Reglas de abandono: una partida con reloj no se puede dejar (20 s) y una sin reloj se pierde a los 2 días sin jugar."""
import time
from datetime import datetime, timedelta, timezone

import chess
import pytest

import backend.servicios.partida.presencia as presencia
from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidasEnMemoria
from backend.servicios.calibracion import MIN_JUGADAS_PARTIDA_VALIDA
from backend.servicios.partida.ciclo_vida import (
    HORAS_INACTIVIDAD_ABANDONO,
    SEGUNDOS_AUSENCIA_CON_RELOJ,
    cerrar_partidas_pendientes,
    dar_por_perdida_si_ausente,
    limpiar_partidas_inactivas,
)

_JUGADAS = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7"]
"""Diez plies (5 del jugador) siempre legales: justo `MIN_JUGADAS_PARTIDA_VALIDA`."""


def _partida(plies: int, control_tiempo_ms: int = 0) -> Partida:
    tablero = chess.Board()
    for san in _JUGADAS[:plies]:
        tablero.push_san(san)
    return Partida(tablero=tablero, nivel=5, usuario_id=1, control_tiempo_ms=control_tiempo_ms)


def _senal_hace(partida: Partida, segundos: float) -> float:
    """Anota una señal de vida de hace `segundos` y devuelve el "ahora" con el que evaluar."""
    ahora = time.monotonic()
    presencia.registrar(partida.id, ahora=ahora - segundos)
    return ahora


def test_con_reloj_ausente_mas_de_20_segundos_se_da_por_perdida() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(2 * MIN_JUGADAS_PARTIDA_VALIDA, control_tiempo_ms=300_000)
    repositorio.guardar(partida)
    ahora = _senal_hace(partida, SEGUNDOS_AUSENCIA_CON_RELOJ + 5)

    assert dar_por_perdida_si_ausente(partida, repositorio, ahora) is True

    guardada = repositorio.obtener(partida.id)
    assert guardada.estado == "abandonada"
    assert guardada.terminada is True
    assert guardada.resultado == "0-1"  # el jugador (blancas) pierde


def test_con_reloj_presente_no_se_toca() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(4, control_tiempo_ms=300_000)
    repositorio.guardar(partida)
    ahora = _senal_hace(partida, SEGUNDOS_AUSENCIA_CON_RELOJ - 5)

    assert dar_por_perdida_si_ausente(partida, repositorio, ahora) is False
    assert repositorio.obtener(partida.id).estado == "en_curso"


def test_con_reloj_sin_ninguna_senal_no_se_da_por_perdida() -> None:
    # Una pantalla que no avisa (app móvil) o un servidor recién reiniciado: no hay base para decir que se fue.
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(4, control_tiempo_ms=300_000)
    repositorio.guardar(partida)

    assert dar_por_perdida_si_ausente(partida, repositorio, time.monotonic() + 3600) is False
    assert repositorio.obtener(partida.id).estado == "en_curso"


def test_sin_reloj_la_ausencia_corta_no_pierde_la_partida() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(4)
    repositorio.guardar(partida)
    ahora = _senal_hace(partida, 3600)

    assert dar_por_perdida_si_ausente(partida, repositorio, ahora) is False


def test_con_reloj_ausente_y_casi_sin_jugadas_se_borra() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(2, control_tiempo_ms=300_000)  # 1 jugada del jugador
    repositorio.guardar(partida)
    ahora = _senal_hace(partida, SEGUNDOS_AUSENCIA_CON_RELOJ + 5)

    assert dar_por_perdida_si_ausente(partida, repositorio, ahora) is True

    with pytest.raises(KeyError):
        repositorio.obtener(partida.id)


def test_el_barrido_da_por_perdida_la_partida_con_reloj_ausente() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(2 * MIN_JUGADAS_PARTIDA_VALIDA, control_tiempo_ms=300_000)
    repositorio.guardar(partida)
    presencia.registrar(partida.id, ahora=time.monotonic() - SEGUNDOS_AUSENCIA_CON_RELOJ - 5)

    limpiar_partidas_inactivas(repositorio)

    assert repositorio.obtener(partida.id).estado == "abandonada"


def test_sin_reloj_a_los_dos_dias_sin_jugar_se_da_por_perdida() -> None:
    assert HORAS_INACTIVIDAD_ABANDONO == 48
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(2 * MIN_JUGADAS_PARTIDA_VALIDA)
    partida.actualizada_en = (datetime.now(timezone.utc) - timedelta(hours=HORAS_INACTIVIDAD_ABANDONO + 1)).isoformat()
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    guardada = repositorio.obtener(partida.id)
    assert guardada.estado == "abandonada"
    assert guardada.resultado == "0-1"


def test_sin_reloj_un_dia_sin_jugar_todavia_se_puede_retomar() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(2 * MIN_JUGADAS_PARTIDA_VALIDA)
    partida.actualizada_en = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    repositorio.guardar(partida)

    limpiar_partidas_inactivas(repositorio)

    assert repositorio.obtener(partida.id).estado == "en_curso"


def test_empezar_otra_partida_da_por_perdida_la_que_se_dejo() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = _partida(2 * MIN_JUGADAS_PARTIDA_VALIDA)
    repositorio.guardar(partida)

    cerrar_partidas_pendientes(repositorio, 1)

    guardada = repositorio.obtener(partida.id)
    assert guardada.estado == "abandonada"
    assert guardada.resultado == "0-1"
