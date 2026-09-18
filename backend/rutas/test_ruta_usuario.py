"""Rutas /usuario (estadísticas, historial — HU14) contra una SQLite en memoria.

`POST /partida` no se usa acá para armar los datos: esa ruta persiste a
través de `servicio_partida._repositorio`, que en este proceso de test elige
`RepositorioPartidasEnMemoria` (no hay `DATABASE_URL` seteada), así que nunca
toca la tabla `partida` de esta base de prueba. En un despliegue real ambas
cosas comparten la misma `DATABASE_URL`, así que esa tabla sí tiene filas
reales; acá se insertan directo con el ORM para probar solo la agregación.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import crear_fabrica_sesiones, crear_tablas
from backend.main import app
from backend.modelos.tablas_orm import PartidaORM
from backend.rutas.ruta_auth import get_db

JUGADOR = {"email": "stats@test.com", "nombre": "Jugadora", "password": "secreto1"}


@pytest.fixture
def contexto():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    crear_tablas(engine)
    fabrica = crear_fabrica_sesiones(engine)

    def _db():
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    # Restaura el override anterior (si había uno) en vez de sacarlo directo —
    # ver el mismo comentario en `test_ruta_auth.py::cliente` sobre por qué,
    # corriendo junto a otras suites que instalan un override propio.
    override_anterior = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _db
    cliente = TestClient(app)
    respuesta = cliente.post("/auth/registro", json=JUGADOR)
    token = respuesta.json()["tokens"]["access_token"]
    usuario_id = respuesta.json()["usuario"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    try:
        yield cliente, headers, usuario_id, fabrica
    finally:
        if override_anterior is not None:
            app.dependency_overrides[get_db] = override_anterior
        else:
            app.dependency_overrides.pop(get_db, None)


def _agregar_partida(fabrica, usuario_id: int, resultado: str | None, tipo_oponente="motor", nivel=10,
                      jugadas_uci="", fecha=None) -> None:
    with fabrica() as sesion:
        sesion.add(
            PartidaORM(
                id=f"partida-{resultado}-{jugadas_uci}-{fecha}",
                usuario_id=usuario_id,
                resultado=resultado,
                tipo="digital",
                fen="fen-cualquiera",
                nivel=nivel,
                tipo_oponente=tipo_oponente,
                jugadas_uci=jugadas_uci,
                fecha=fecha or datetime.now(timezone.utc),
            )
        )
        sesion.commit()


def test_estadisticas_sin_token_da_401(contexto) -> None:
    cliente, _, _, _ = contexto
    assert cliente.get("/usuario/estadisticas").status_code == 401


def test_estadisticas_sin_partidas_devuelve_todo_en_cero(contexto) -> None:
    cliente, headers, _, _ = contexto
    respuesta = cliente.get("/usuario/estadisticas", headers=headers)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_partidas"] == 0
    assert cuerpo["win_percent_promedio"] == 0.0
    assert cuerpo["racha_victoria_actual"] == 0
    assert cuerpo["top_errores"] == []


def test_estadisticas_cuenta_ganadas_perdidas_y_tablas(contexto) -> None:
    cliente, headers, usuario_id, fabrica = contexto
    _agregar_partida(fabrica, usuario_id, "1-0", fecha=datetime(2026, 1, 1, tzinfo=timezone.utc))
    _agregar_partida(fabrica, usuario_id, "0-1", fecha=datetime(2026, 1, 2, tzinfo=timezone.utc))
    _agregar_partida(fabrica, usuario_id, "1/2-1/2", fecha=datetime(2026, 1, 3, tzinfo=timezone.utc))

    respuesta = cliente.get("/usuario/estadisticas", headers=headers)

    cuerpo = respuesta.json()
    assert cuerpo["total_partidas"] == 3
    assert cuerpo["partidas_ganadas"] == 1
    assert cuerpo["partidas_perdidas"] == 1
    assert cuerpo["partidas_tablas"] == 1
    assert cuerpo["win_percent_promedio"] == pytest.approx(33.33, rel=1e-2)


def test_estadisticas_racha_de_victorias_se_corta_en_la_primera_no_victoria(contexto) -> None:
    cliente, headers, usuario_id, fabrica = contexto
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _agregar_partida(fabrica, usuario_id, "0-1", fecha=base)
    _agregar_partida(fabrica, usuario_id, "1-0", fecha=base + timedelta(days=1))
    _agregar_partida(fabrica, usuario_id, "1-0", fecha=base + timedelta(days=2))

    respuesta = cliente.get("/usuario/estadisticas", headers=headers)

    assert respuesta.json()["racha_victoria_actual"] == 2


def test_estadisticas_no_mezcla_partidas_de_otro_usuario(contexto) -> None:
    cliente, headers, usuario_id, fabrica = contexto
    _agregar_partida(fabrica, usuario_id + 999, "1-0", fecha=datetime.now(timezone.utc))

    respuesta = cliente.get("/usuario/estadisticas", headers=headers)

    assert respuesta.json()["total_partidas"] == 0


def test_historial_partidas_sin_token_da_401(contexto) -> None:
    cliente, _, _, _ = contexto
    assert cliente.get("/usuario/historial-partidas").status_code == 401


def test_historial_partidas_devuelve_mas_reciente_primero_con_cantidad_de_jugadas(contexto) -> None:
    cliente, headers, usuario_id, fabrica = contexto
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _agregar_partida(fabrica, usuario_id, "1-0", jugadas_uci="e2e4 e7e5", fecha=base)
    _agregar_partida(fabrica, usuario_id, None, jugadas_uci="d2d4", fecha=base + timedelta(days=1))

    respuesta = cliente.get("/usuario/historial-partidas", headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 2
    assert len(cuerpo["partidas"]) == 2
    assert cuerpo["partidas"][0]["cantidad_jugadas"] == 1
    assert cuerpo["partidas"][0]["resultado"] is None
    assert cuerpo["partidas"][1]["cantidad_jugadas"] == 2
    assert cuerpo["partidas"][1]["resultado"] == "1-0"


def test_historial_partidas_respeta_limit_y_offset(contexto) -> None:
    cliente, headers, usuario_id, fabrica = contexto
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(3):
        _agregar_partida(fabrica, usuario_id, "1-0", jugadas_uci="e2e4", fecha=base + timedelta(days=i))

    respuesta = cliente.get("/usuario/historial-partidas?limit=1&offset=1", headers=headers)

    cuerpo = respuesta.json()
    assert cuerpo["total"] == 3
    assert len(cuerpo["partidas"]) == 1
