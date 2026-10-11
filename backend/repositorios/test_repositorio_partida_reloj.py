"""El reloj y el tiempo de cada jugada se guardan con la partida (SQLite en memoria)."""
import pytest
from sqlalchemy import create_engine

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidasPostgres


@pytest.fixture()
def repositorio() -> RepositorioPartidasPostgres:
    engine = create_engine("sqlite:///:memory:")
    crear_tablas(engine)
    return RepositorioPartidasPostgres(crear_fabrica_sesiones(engine))


def test_el_reloj_y_los_tiempos_por_jugada_sobreviven_al_guardado(repositorio: RepositorioPartidasPostgres) -> None:
    partida = Partida(nivel=5, control_tiempo_ms=600_000)
    partida.tablero.push_san("e4")
    partida.tablero.push_san("e5")
    partida.tiempo_blancas_ms = 541_000
    partida.tiempo_negras_ms = 598_700
    partida.tiempos_jugadas_ms = [None, 1300]

    repositorio.guardar(partida)
    leida = repositorio.obtener(partida.id)

    assert leida.control_tiempo_ms == 600_000
    assert (leida.restante_blancas_ms, leida.restante_negras_ms) == (541_000, 598_700)
    assert leida.tiempos_jugadas_ms == [None, 1300]


def test_una_partida_sin_reloj_se_lee_sin_reloj_ni_tiempos(repositorio: RepositorioPartidasPostgres) -> None:
    partida = Partida(nivel=5)
    repositorio.guardar(partida)

    leida = repositorio.obtener(partida.id)

    assert leida.control_tiempo_ms == 0
    assert leida.tiempos_jugadas_ms == []
    assert leida.duracion_ms == 0


def test_actualizar_una_partida_guardada_pisa_el_reloj(repositorio: RepositorioPartidasPostgres) -> None:
    partida = Partida(nivel=5, control_tiempo_ms=300_000)
    repositorio.guardar(partida)
    partida.tiempo_blancas_ms = 120_000
    repositorio.guardar(partida)

    assert repositorio.obtener(partida.id).restante_blancas_ms == 120_000
