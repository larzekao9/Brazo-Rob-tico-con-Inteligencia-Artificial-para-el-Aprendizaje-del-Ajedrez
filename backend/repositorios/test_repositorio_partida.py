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


def test_registrar_jugada_no_rompe_sin_tabla_jugada_en_memoria() -> None:
    # No-op documentado (ver docstring de `RepositorioPartidasEnMemoria.registrar_jugada`):
    # no hay tabla `jugada` en memoria a la que escribir.
    repositorio = RepositorioPartidasEnMemoria()
    repositorio.registrar_jugada("no-existe", 1, "fen", "e2e4", "jugador")


def test_eliminar_borra_la_partida() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    partida = Partida(nivel=5)
    repositorio.guardar(partida)

    repositorio.eliminar(partida.id)

    with pytest.raises(KeyError):
        repositorio.obtener(partida.id)


def test_eliminar_partida_inexistente_no_lanza_error() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    repositorio.eliminar("no-existe")


def test_listar_por_usuario_solo_devuelve_las_del_usuario_mas_reciente_primero() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    primera = Partida(nivel=5, usuario_id=1)
    repositorio.guardar(primera)
    de_otro = Partida(nivel=5, usuario_id=2)
    repositorio.guardar(de_otro)
    segunda = Partida(nivel=5, usuario_id=1)
    repositorio.guardar(segunda)

    resultado = repositorio.listar_por_usuario(1)

    assert [partida.id for partida in resultado] == [segunda.id, primera.id]


def test_listar_por_usuario_vacio_si_no_tiene_partidas() -> None:
    repositorio = RepositorioPartidasEnMemoria()
    assert repositorio.listar_por_usuario(1) == []
