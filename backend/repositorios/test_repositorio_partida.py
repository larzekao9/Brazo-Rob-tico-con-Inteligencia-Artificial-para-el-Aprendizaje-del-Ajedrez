import pytest

from backend.modelos.partida import Partida
from backend.repositorios.repositorio_partida import RepositorioPartidasEnMemoria


def test_guardar_y_obtener_devuelve_la_misma_partida() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = Partida(nivel=10)

    repositorio.guardar(partida)

    assert repositorio.obtener(partida.id) is partida


def test_obtener_partida_inexistente_lanza_keyerror() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    with pytest.raises(KeyError):
        repositorio.obtener("no-existe")


def test_repositorios_distintos_no_comparten_estado() -> None:
    repositorio_a = RepositorioPartidasEnMemoria()
    repositorio_b = RepositorioPartidasEnMemoria()
    partida = Partida()

    repositorio_a.guardar(partida)

    with pytest.raises(KeyError):
        repositorio_b.obtener(partida.id)


def test_listar_devuelve_todas_las_guardadas_mas_reciente_primero() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    primera = Partida()
    segunda = Partida()

    repositorio.guardar(primera)
    repositorio.guardar(segunda)

    assert repositorio.listar() == [segunda, primera]


def test_listar_vacio_si_no_hay_partidas_guardadas() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    assert repositorio.listar() == []
