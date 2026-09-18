"""Tests de `RepositorioPartidasPostgres` contra SQLite en memoria.

No hace falta un Postgres real corriendo para probar la lógica del
repositorio: las tablas de `backend/modelos/tablas_orm.py` no usan ningún
tipo específico de Postgres, así que SQLAlchemy las crea igual sobre SQLite.
Esto prueba el mapeo objeto-relacional y la traducción de/hacia el
dataclass de dominio; la conexión real a Postgres (URL, credenciales) se
prueba manualmente corriendo el backend con `DATABASE_URL` seteada.
"""
import chess
import pytest
from sqlalchemy import create_engine, select

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.modelos.partida import Partida
from backend.modelos.tablas_orm import JugadaORM
from backend.repositorios.repositorio_partida import RepositorioPartidasPostgres


@pytest.fixture()
def repositorio() -> RepositorioPartidasPostgres:
    engine = create_engine("sqlite:///:memory:")
    crear_tablas(engine)
    return RepositorioPartidasPostgres(crear_fabrica_sesiones(engine))


def test_guardar_y_obtener_reconstruye_la_partida(repositorio: RepositorioPartidasPostgres) -> None:
    partida = Partida(nivel=10, tipo_oponente="motor")
    partida.tablero.push_san("e4")
    partida.tablero.push_san("e5")

    repositorio.guardar(partida)
    partida_leida = repositorio.obtener(partida.id)

    assert partida_leida.id == partida.id
    assert partida_leida.nivel == 10
    assert partida_leida.tipo_oponente == "motor"
    assert partida_leida.fen == partida.fen
    assert partida_leida.jugadas_san == ["e4", "e5"]  # se reconstruye jugada por jugada


def test_obtener_partida_inexistente_lanza_keyerror(repositorio: RepositorioPartidasPostgres) -> None:
    with pytest.raises(KeyError):
        repositorio.obtener("no-existe")


def test_guardar_dos_veces_actualiza_en_vez_de_duplicar(repositorio: RepositorioPartidasPostgres) -> None:
    partida = Partida(nivel=5)
    repositorio.guardar(partida)

    partida.tablero.push_san("d4")
    repositorio.guardar(partida)

    assert len(repositorio.listar()) == 1
    assert repositorio.obtener(partida.id).jugadas_san == ["d4"]


def test_listar_devuelve_mas_reciente_primero(repositorio: RepositorioPartidasPostgres) -> None:
    primera = Partida()
    repositorio.guardar(primera)
    segunda = Partida()
    repositorio.guardar(segunda)

    ids_listados = [partida.id for partida in repositorio.listar()]
    assert ids_listados == [segunda.id, primera.id]


def test_listar_vacio_si_no_hay_partidas_guardadas(repositorio: RepositorioPartidasPostgres) -> None:
    assert repositorio.listar() == []


def test_guardar_persiste_el_usuario_dueno_de_la_partida(repositorio: RepositorioPartidasPostgres) -> None:
    partida = Partida(nivel=5, usuario_id=42)
    repositorio.guardar(partida)

    assert repositorio.obtener(partida.id).usuario_id == 42


def test_registrar_jugada_guarda_una_fila_en_la_tabla_jugada(
    repositorio: RepositorioPartidasPostgres,
) -> None:
    partida = Partida(nivel=5)
    repositorio.guardar(partida)

    repositorio.registrar_jugada(partida.id, 1, partida.fen, "e2e4", "jugador")

    with repositorio._fabrica_sesiones() as sesion:
        filas = sesion.scalars(select(JugadaORM).where(JugadaORM.partida_id == partida.id)).all()

    assert len(filas) == 1
    assert filas[0].numero == 1
    assert filas[0].fen_antes == partida.fen
    assert filas[0].movimiento == "e2e4"
    assert filas[0].decidido_por == "jugador"


def test_registrar_jugada_dos_veces_guarda_dos_filas_distintas(
    repositorio: RepositorioPartidasPostgres,
) -> None:
    partida = Partida(nivel=5)
    repositorio.guardar(partida)

    repositorio.registrar_jugada(partida.id, 1, partida.fen, "e2e4", "jugador")
    repositorio.registrar_jugada(partida.id, 2, partida.fen, "e7e5", "motor")

    with repositorio._fabrica_sesiones() as sesion:
        filas = sesion.scalars(
            select(JugadaORM).where(JugadaORM.partida_id == partida.id).order_by(JugadaORM.numero)
        ).all()

    assert [fila.decidido_por for fila in filas] == ["jugador", "motor"]
