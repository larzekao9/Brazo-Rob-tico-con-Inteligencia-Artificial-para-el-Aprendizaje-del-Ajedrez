"""`crear_repositorio_partidas` (sección 7): en memoria por defecto, Postgres si `DATABASE_URL` está seteada."""
from backend.repositorios.repositorio_partida import (
    RepositorioPartidasEnMemoria,
    crear_repositorio_partidas,
)


def test_sin_database_url_devuelve_repositorio_en_memoria(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert isinstance(crear_repositorio_partidas(), RepositorioPartidasEnMemoria)
