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


def test_estadisticas_top_errores_cuenta_blunder_tras_analisis_completo(contexto, monkeypatch) -> None:
    """Extremo a extremo: HU5 (`/analisis-completo`) persiste la evaluación de
    cada jugada vía `actualizar_evaluacion_jugada`, y HU14 (`/estadisticas`)
    la usa para armar `top_errores` sin volver a llamar a Stockfish.

    Fuerza el "Fool's Mate" clásico (1.f3 e5 2.g4 Qh4#) guionando la
    respuesta del "motor" para las negras — así el resultado es
    determinístico (no depende de qué juegue Stockfish) mientras que blancas
    (el jugador) sí hacen jugadas reales, incluido el blunder real (2.g4??,
    que tira a la basura cualquier chance y deja mate en 1 para las negras).
    """
    import backend.servicios.partida.servicio_partida as servicio_partida_mod
    from backend.repositorios.repositorio_partida import RepositorioPartidasPostgres

    cliente, headers, usuario_id, fabrica = contexto
    # `servicio_partida._repositorio` es en memoria por defecto en este
    # proceso de test (no hay `DATABASE_URL`) — para probar el flujo
    # completo hace falta que las partidas y jugadas creadas por `/partida`
    # y `/mover` caigan en la misma base SQLite que usa `/usuario/estadisticas`.
    monkeypatch.setattr(servicio_partida_mod, "_repositorio", RepositorioPartidasPostgres(fabrica))

    jugadas_negras = iter(["e5", "Qh4#"])

    class _EstrategiaGuionada:
        def decidir_jugada(self, fen: str) -> str:
            return next(jugadas_negras)

    monkeypatch.setattr(
        servicio_partida_mod,
        "crear_estrategia_jugada",
        lambda tipo_oponente, nivel=20: _EstrategiaGuionada(),
    )

    partida_id = cliente.post("/partida", json={"nivel": 10}, headers=headers).json()["id"]

    resp1 = cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "f2f3"})
    assert resp1.status_code == 200
    assert resp1.json()["terminada"] is False

    resp2 = cliente.post(f"/partida/{partida_id}/mover", json={"jugada": "g2g4"})
    assert resp2.status_code == 200
    assert resp2.json()["terminada"] is True
    assert resp2.json()["resultado"] == "0-1"

    resp_analisis = cliente.get(f"/partida/{partida_id}/analisis-completo")
    assert resp_analisis.status_code == 200

    resp_stats = cliente.get("/usuario/estadisticas", headers=headers)
    assert resp_stats.status_code == 200
    top_errores = resp_stats.json()["top_errores"]
    assert any(item["cantidad"] > 0 for item in top_errores)
    assert any(item["tipo"] == "blunder" and item["cantidad"] > 0 for item in top_errores)


def test_historial_partidas_respeta_limit_y_offset(contexto) -> None:
    cliente, headers, usuario_id, fabrica = contexto
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(3):
        _agregar_partida(fabrica, usuario_id, "1-0", jugadas_uci="e2e4", fecha=base + timedelta(days=i))

    respuesta = cliente.get("/usuario/historial-partidas?limit=1&offset=1", headers=headers)

    cuerpo = respuesta.json()
    assert cuerpo["total"] == 3
    assert len(cuerpo["partidas"]) == 1
