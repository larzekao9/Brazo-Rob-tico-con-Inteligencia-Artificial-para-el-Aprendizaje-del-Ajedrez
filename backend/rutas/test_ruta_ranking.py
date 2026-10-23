"""Ranking por nivel y reporte de un curso (SQLite en memoria)."""
import uuid
from datetime import datetime, timedelta, timezone

import chess

from backend.modelos.tablas_orm import CalibracionORM, PartidaORM, UsuarioORM
from backend.rutas.test_ruta_cursos import _crear, _solo_principal, _unirse
from backend.rutas.test_ruta_gestion_usuarios import contexto  # noqa: F401  (fixture compartida)
from backend.servicios.curso.servicio_reporte import nombre_publico


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _calibrar(fabrica, usuario_id: int, nivel: int, precisiones: list[float], nombre: str | None = None, hace_dias: int = 0) -> None:
    """Le deja `nivel` al usuario y una partida calibrada por cada precisión de `precisiones`."""
    with fabrica() as sesion:
        usuario = sesion.get(UsuarioORM, usuario_id)
        usuario.nivel_estimado, usuario.rango_estimado = nivel, "Intermedio"
        if nombre:
            usuario.nombre = nombre
        for precision in precisiones:
            sesion.add(
                CalibracionORM(
                    usuario_id=usuario_id, partida_id=uuid.uuid4().hex, precision_global=precision, nivel_partida=nivel,
                    rango_partida="Intermedio", total_jugadas=20, creado_en=_ahora() - timedelta(days=hace_dias),
                )
            )
        sesion.commit()


def _partida(fabrica, usuario_id: int, hace_dias: int = 0) -> None:
    with fabrica() as sesion:
        sesion.add(
            PartidaORM(
                id=uuid.uuid4().hex, usuario_id=usuario_id, tipo="digital", fen=chess.STARTING_FEN, nivel=8,
                tipo_oponente="motor", jugadas_uci="e2e4", estado="terminada", iniciada_en=_ahora() - timedelta(days=hace_dias),
            )
        )
        sesion.commit()


def _ranking(cliente, jugador, **parametros):
    return cliente.get("/cursos/ranking", params=parametros, headers=jugador["headers"])


def test_nombre_publico_abrevia_el_apellido() -> None:
    assert nombre_publico("Ana María Pérez") == "Ana P."
    assert nombre_publico("  luis   arze kao ") == "luis K."
    assert nombre_publico("Pelé") == "Pelé"
    assert nombre_publico("") == "Jugador"


def test_el_ranking_de_un_curso_ordena_por_nivel_y_muestra_nombres_abreviados(contexto) -> None:
    cliente, registrar, fabrica = contexto
    profe = registrar("prof@test.com", "facilitador")
    ana, beto, carla, sin_partidas = registrar("ana@test.com"), registrar("beto@test.com"), registrar("carla@test.com"), registrar("sin@test.com")
    _calibrar(fabrica, ana["id"], 10, [70, 72, 74], nombre="Ana María Pérez")
    _calibrar(fabrica, beto["id"], 12, [80], nombre="Beto Gómez")
    _calibrar(fabrica, carla["id"], 7, [50, 55, 60], nombre="Carla Díaz")
    curso = _crear(cliente, profe)
    for jugador in (ana, beto, carla, sin_partidas):
        _unirse(cliente, jugador, curso["codigo"])

    respuesta = _ranking(cliente, ana)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["alcance"] == "curso" and cuerpo["curso"] == "Ajedrez 1ro A" and cuerpo["total"] == 3  # el que no jugó no figura
    assert [(f["puesto"], f["nombre"], f["nivel"]) for f in cuerpo["jugadores"]] == [(1, "Beto G.", 12), (2, "Ana P.", 10), (3, "Carla D.", 7)]
    assert [f["confirmado"] for f in cuerpo["jugadores"]] == [False, True, True]  # Beto tiene 1 partida: nivel provisional
    assert [f["soy_yo"] for f in cuerpo["jugadores"]] == [False, True, False] and cuerpo["mi_puesto"] is None


def test_si_quedo_fuera_del_tope_se_agrega_la_fila_propia(contexto) -> None:
    cliente, registrar, fabrica = contexto
    profe = registrar("prof@test.com", "facilitador")
    jugadores = [registrar(f"j{n}@test.com") for n in range(4)]
    curso = _crear(cliente, profe)
    for n, jugador in enumerate(jugadores):
        _calibrar(fabrica, jugador["id"], 15 - n, [60])
        _unirse(cliente, jugador, curso["codigo"])

    cuerpo = _ranking(cliente, jugadores[3], limite=2).json()

    assert [f["puesto"] for f in cuerpo["jugadores"]] == [1, 2] and cuerpo["total"] == 4
    assert cuerpo["mi_puesto"]["puesto"] == 4 and cuerpo["mi_puesto"]["soy_yo"] is True


def test_el_ranking_general_son_los_jugadores_sin_curso_y_no_incluye_facilitadores_ni_inactivos(contexto) -> None:
    cliente, registrar, fabrica = contexto
    admin = registrar("admin@test.com", "facilitador")
    profe = registrar("prof@test.com", "facilitador")
    libre1, libre2, de_curso, inactivo = registrar("l1@test.com"), registrar("l2@test.com"), registrar("c@test.com"), registrar("i@test.com")
    for jugador, nivel in ((libre1, 9), (libre2, 5), (de_curso, 18), (inactivo, 20)):
        _calibrar(fabrica, jugador["id"], nivel, [60])
    _calibrar(fabrica, profe["id"], 20, [90])  # un facilitador con calibraciones no entra
    _unirse(cliente, de_curso, _crear(cliente, profe)["codigo"])
    cliente.patch(f"/auth/usuarios/{inactivo['id']}", json={"activo": False}, headers=admin["headers"])

    cuerpo = _ranking(cliente, libre2).json()

    assert cuerpo["alcance"] == "general" and cuerpo["curso"] is None and cuerpo["total"] == 2
    assert [f["nivel"] for f in cuerpo["jugadores"]] == [9, 5]  # el de curso, el inactivo y el facilitador quedan afuera


def test_el_mismo_nivel_y_precision_comparten_puesto(contexto) -> None:
    cliente, registrar, fabrica = contexto
    uno, dos, tres = registrar("a@test.com"), registrar("b@test.com"), registrar("c@test.com")
    _calibrar(fabrica, uno["id"], 8, [60])
    _calibrar(fabrica, dos["id"], 8, [60])
    _calibrar(fabrica, tres["id"], 8, [50])

    cuerpo = _ranking(cliente, uno).json()

    assert [f["puesto"] for f in cuerpo["jugadores"]] == [1, 1, 3]


def test_un_facilitador_ve_el_ranking_de_sus_cursos_y_un_jugador_no_puede_pedir_el_de_otro(contexto, monkeypatch) -> None:
    cliente, registrar, fabrica = contexto
    profe, otro, jugador = registrar("prof@test.com", "facilitador"), registrar("otro@test.com", "facilitador"), registrar("j@test.com")
    curso = _crear(cliente, profe)
    _calibrar(fabrica, jugador["id"], 6, [55])
    _unirse(cliente, jugador, curso["codigo"])
    _solo_principal(monkeypatch, "nadie@test.com")

    propio = _ranking(cliente, profe, curso_id=curso["id"])
    assert propio.status_code == 200 and propio.json()["total"] == 1
    assert _ranking(cliente, otro, curso_id=curso["id"]).status_code == 404
    assert _ranking(cliente, jugador, curso_id=curso["id"]).status_code == 403
    assert cliente.get("/cursos/ranking").status_code == 401


def test_el_reporte_del_curso_calcula_los_indicadores_del_piloto(contexto, monkeypatch) -> None:
    cliente, registrar, fabrica = contexto
    profe, otro, jugador_ajeno = registrar("prof@test.com", "facilitador"), registrar("otro@test.com", "facilitador"), registrar("x@test.com")
    activo, quieto = registrar("a@test.com"), registrar("q@test.com")
    curso = _crear(cliente, profe)
    for jugador in (activo, quieto):
        _unirse(cliente, jugador, curso["codigo"])
    _calibrar(fabrica, activo["id"], 9, [40], nombre="Ana María Pérez", hace_dias=21)  # primera semana
    _calibrar(fabrica, activo["id"], 9, [70], hace_dias=1)  # última semana
    _partida(fabrica, activo["id"], hace_dias=21)
    _partida(fabrica, activo["id"], hace_dias=2)
    _partida(fabrica, activo["id"], hace_dias=1)
    _solo_principal(monkeypatch, "nadie@test.com")

    respuesta = cliente.get(f"/cursos/{curso['id']}/reporte", headers=profe["headers"])

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["curso"] == {"id": curso["id"], "nombre": "Ajedrez 1ro A", "cupo": 60, "alumnos": 2}
    resumen = cuerpo["resumen"]
    assert resumen["alumnos_activos_7_dias"] == 1 and resumen["porcentaje_activos"] == 50.0
    assert resumen["partidas_7_dias"] == 2 and resumen["partidas_por_alumno_semana"] == 1.0
    assert (resumen["precision_primera_semana"], resumen["precision_ultima_semana"], resumen["variacion_precision"]) == (40.0, 70.0, 30.0)
    fila_activo, fila_quieto = cuerpo["alumnos"]  # primero los que tienen puesto
    assert fila_activo["nombre"] == "Ana María Pérez" and fila_activo["puesto"] == 1 and fila_activo["partidas"] == 3
    assert fila_activo["partidas_7_dias"] == 2 and fila_activo["ultima_partida"] is not None
    assert fila_quieto["puesto"] is None and fila_quieto["partidas"] == 0 and fila_quieto["ultima_partida"] is None

    assert cliente.get(f"/cursos/{curso['id']}/reporte", headers=otro["headers"]).status_code == 404
    assert cliente.get(f"/cursos/{curso['id']}/reporte", headers=jugador_ajeno["headers"]).status_code == 403


def test_el_reporte_de_un_curso_vacio_no_falla_y_el_principal_puede_ver_cualquiera(contexto, monkeypatch) -> None:
    cliente, registrar, _ = contexto
    principal, comun = registrar("admin@test.com", "facilitador"), registrar("comun@test.com", "facilitador")
    curso = _crear(cliente, comun)
    _solo_principal(monkeypatch, "admin@test.com")

    cuerpo = cliente.get(f"/cursos/{curso['id']}/reporte", headers=principal["headers"]).json()

    assert cuerpo["alumnos"] == [] and cuerpo["resumen"]["porcentaje_activos"] is None
    assert cuerpo["resumen"]["precision_primera_semana"] is None and cuerpo["resumen"]["variacion_precision"] is None
