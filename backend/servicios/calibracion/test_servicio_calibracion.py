"""Tests de `servicio_calibracion.py` contra una SQLite en memoria (sin Stockfish ni HTTP)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.database import Base, crear_fabrica_sesiones
from backend.modelos.tablas_orm import CalibracionORM, UsuarioORM
from backend.servicios.aprendizaje.niveles import NIVEL_MAX_MODELO
from backend.servicios.auth import actualizar_nivel_estimado
from backend.servicios.calibracion import (
    MAX_CALIBRACIONES_HISTORIAL,
    MIN_JUGADAS_CALIBRACION,
    NIVEL_DIAGNOSTICO,
    VENTANA_CALIBRACION,
    contar_calibraciones,
    contar_calibraciones_por_usuario,
    escala_niveles,
    estado_nivel_jugador,
    precision_para_alcanzar_nivel,
    registrar_calibracion,
)
from backend.servicios.calibracion import servicio_calibracion
from backend.servicios.retroalimentacion import calcular_rango_desde_precision
from backend.servicios.retroalimentacion.servicio_retroalimentacion import BANDA_NIVEL_POR_RANGO


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with crear_fabrica_sesiones(engine)() as sesion:
        yield sesion


def _usuario(db, email: str = "ana@test.com", rol: str = "jugador") -> UsuarioORM:
    usuario = UsuarioORM(email=email, nombre="Ana", rol=rol, activo=True)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def _resumen(precision: float, jugadas_jugador: int = MIN_JUGADAS_CALIBRACION) -> dict:
    return {
        "precision_global": 99.0,
        "total_jugadas": jugadas_jugador * 2,
        "precision_jugador": precision,
        "total_jugadas_jugador": jugadas_jugador,
    }


def _filas(db, usuario_id: int) -> list[CalibracionORM]:
    return list(db.scalars(select(CalibracionORM).where(CalibracionORM.usuario_id == usuario_id)))


def test_constantes_de_calibracion() -> None:
    assert VENTANA_CALIBRACION == 3
    assert MIN_JUGADAS_CALIBRACION == 5
    assert NIVEL_DIAGNOSTICO == 8


def test_primera_calibracion_es_el_diagnostico_y_fija_el_nivel(db) -> None:
    usuario = _usuario(db)

    respuesta = registrar_calibracion(db, usuario, "p1", _resumen(60.0))

    nivel, rango = calcular_rango_desde_precision(60.0)
    assert respuesta["registrada"] is True
    assert respuesta["motivo"] is None
    assert respuesta["es_diagnostico"] is True
    assert respuesta["precision_partida"] == 60.0
    assert respuesta["precision_promedio"] == 60.0
    assert respuesta["partidas_consideradas"] == 1
    assert (respuesta["nivel_anterior"], respuesta["rango_anterior"]) == (None, None)
    assert (respuesta["nivel"], respuesta["rango"]) == (nivel, rango)
    assert respuesta["cambio_de_rango"] is False
    assert respuesta["cambio_de_nivel"] == 0
    db.refresh(usuario)
    assert (usuario.nivel_estimado, usuario.rango_estimado) == (nivel, rango)
    fila = _filas(db, usuario.id)[0]
    assert (fila.partida_id, fila.precision_global, fila.total_jugadas) == ("p1", 60.0, MIN_JUGADAS_CALIBRACION)
    assert (fila.nivel_partida, fila.rango_partida) == (nivel, rango)


def test_la_respuesta_tiene_exactamente_los_campos_del_contrato(db) -> None:
    respuesta = registrar_calibracion(db, _usuario(db), "p1", _resumen(60.0))

    assert set(respuesta) == {
        "registrada", "motivo", "es_diagnostico", "precision_partida", "precision_promedio",
        "partidas_consideradas", "nivel_anterior", "rango_anterior", "nivel", "rango",
        "cambio_de_rango", "cambio_de_nivel",
    }


def test_registrar_la_misma_partida_dos_veces_deja_una_sola_fila(db) -> None:
    usuario = _usuario(db)
    primera = registrar_calibracion(db, usuario, "p1", _resumen(60.0))

    segunda = registrar_calibracion(db, usuario, "p1", _resumen(10.0))

    assert primera["registrada"] is True
    assert segunda["registrada"] is False
    assert segunda["motivo"] == "ya_registrada"
    assert segunda["es_diagnostico"] is False
    assert segunda["precision_partida"] == 60.0
    assert segunda["nivel"] == segunda["nivel_anterior"] == primera["nivel"]
    assert segunda["cambio_de_nivel"] == 0
    assert segunda["cambio_de_rango"] is False
    assert contar_calibraciones(db, usuario.id) == 1


def test_el_nivel_es_el_promedio_de_las_ultimas_tres_calibraciones(db) -> None:
    usuario = _usuario(db)
    precisiones = [20.0, 50.0, 80.0, 95.0]

    respuestas = [
        registrar_calibracion(db, usuario, f"p{i}", _resumen(precision))
        for i, precision in enumerate(precisiones)
    ]

    for indice, esperado in enumerate([20.0, (20 + 50) / 2, (20 + 50 + 80) / 3, (50 + 80 + 95) / 3]):
        nivel, rango = calcular_rango_desde_precision(esperado)
        assert respuestas[indice]["precision_promedio"] == round(esperado, 2)
        assert (respuestas[indice]["nivel"], respuestas[indice]["rango"]) == (nivel, rango)
    assert [r["partidas_consideradas"] for r in respuestas] == [1, 2, 3, 3]
    assert respuestas[3]["nivel_anterior"] == respuestas[2]["nivel"]
    assert respuestas[3]["cambio_de_nivel"] == respuestas[3]["nivel"] - respuestas[2]["nivel"]
    assert [r["es_diagnostico"] for r in respuestas] == [True, False, False, False]
    db.refresh(usuario)
    assert usuario.nivel_estimado == respuestas[3]["nivel"]


def test_reabrir_una_partida_vieja_no_revierte_el_nivel(db) -> None:
    usuario = _usuario(db)
    for i, precision in enumerate([20.0, 90.0, 95.0]):
        registrar_calibracion(db, usuario, f"p{i}", _resumen(precision))
    db.refresh(usuario)
    nivel_vigente = usuario.nivel_estimado

    repeticion = registrar_calibracion(db, usuario, "p0", _resumen(20.0))

    assert repeticion["motivo"] == "ya_registrada"
    db.refresh(usuario)
    assert usuario.nivel_estimado == nivel_vigente == repeticion["nivel"]
    assert contar_calibraciones(db, usuario.id) == 3


def test_cambio_de_rango_y_de_nivel_respecto_al_valor_anterior(db) -> None:
    usuario = _usuario(db)
    actualizar_nivel_estimado(db, usuario, 3, "Principiante")

    respuesta = registrar_calibracion(db, usuario, "p1", _resumen(90.0))

    nivel, rango = calcular_rango_desde_precision(90.0)
    assert rango == "Avanzado"
    assert (respuesta["nivel_anterior"], respuesta["rango_anterior"]) == (3, "Principiante")
    assert respuesta["cambio_de_rango"] is True
    assert respuesta["cambio_de_nivel"] == nivel - 3


def test_partida_con_pocas_jugadas_del_jugador_no_calibra(db) -> None:
    usuario = _usuario(db)

    respuesta = registrar_calibracion(db, usuario, "corta", _resumen(100.0, jugadas_jugador=MIN_JUGADAS_CALIBRACION - 1))

    assert respuesta["registrada"] is False
    assert respuesta["motivo"] == "partida_incompleta"
    assert respuesta["nivel"] is None
    assert contar_calibraciones(db, usuario.id) == 0
    db.refresh(usuario)
    assert usuario.nivel_estimado is None


def test_partida_con_exactamente_el_minimo_de_jugadas_si_calibra(db) -> None:
    respuesta = registrar_calibracion(
        db, _usuario(db), "justa", _resumen(70.0, jugadas_jugador=MIN_JUGADAS_CALIBRACION)
    )

    assert respuesta["registrada"] is True


def test_partida_incompleta_conserva_el_nivel_vigente(db) -> None:
    usuario = _usuario(db)
    registrar_calibracion(db, usuario, "p1", _resumen(60.0))
    db.refresh(usuario)

    respuesta = registrar_calibracion(db, usuario, "corta", _resumen(0.0, jugadas_jugador=2))

    assert respuesta["motivo"] == "partida_incompleta"
    assert respuesta["nivel"] == respuesta["nivel_anterior"] == usuario.nivel_estimado
    assert respuesta["partidas_consideradas"] == 1


def test_sin_jugadas_del_jugador_evaluadas_no_calibra(db) -> None:
    resumen = {"precision_global": 50.0, "total_jugadas": 0, "precision_jugador": None, "total_jugadas_jugador": 0}

    assert registrar_calibracion(db, _usuario(db), "vacia", resumen)["motivo"] == "partida_incompleta"


def test_resumen_sin_campos_del_jugador_usa_la_precision_global(db) -> None:
    resumen = {"precision_global": 30.0, "total_jugadas": MIN_JUGADAS_CALIBRACION}

    respuesta = registrar_calibracion(db, _usuario(db), "p1", resumen)

    assert respuesta["registrada"] is True
    assert respuesta["precision_partida"] == 30.0
    assert (respuesta["nivel"], respuesta["rango"]) == calcular_rango_desde_precision(30.0)


def test_usa_la_precision_del_jugador_y_no_la_de_ambos_bandos(db) -> None:
    resumen = {"precision_global": 95.0, "total_jugadas": 20, "precision_jugador": 40.0, "total_jugadas_jugador": 10}

    respuesta = registrar_calibracion(db, _usuario(db), "p1", resumen)

    assert respuesta["precision_partida"] == 40.0
    assert respuesta["nivel"] == calcular_rango_desde_precision(40.0)[0]


def test_dueno_facilitador_no_calibra(db) -> None:
    facilitador = _usuario(db, email="prof@test.com", rol="facilitador")

    respuesta = registrar_calibracion(db, facilitador, "p1", _resumen(90.0))

    assert respuesta["registrada"] is False
    assert respuesta["motivo"] == "dueno_no_jugador"
    assert contar_calibraciones(db, facilitador.id) == 0
    db.refresh(facilitador)
    assert facilitador.nivel_estimado is None


def test_partida_sin_dueno_no_calibra(db) -> None:
    respuesta = registrar_calibracion(db, None, "p1", _resumen(90.0))

    assert respuesta["registrada"] is False
    assert respuesta["motivo"] == "sin_dueno"
    assert respuesta["nivel"] is None
    assert respuesta["partidas_consideradas"] == 0


def test_carrera_entre_dos_pedidos_de_la_misma_partida_no_duplica(db, monkeypatch) -> None:
    """Si otro pedido inserta la fila entre la comprobación y el guardado, la
    restricción única lo detecta y la respuesta es `ya_registrada`."""
    usuario = _usuario(db)
    registrar_calibracion(db, usuario, "p1", _resumen(60.0))
    buscar_real = servicio_calibracion._buscar_calibracion
    llamadas = []

    def buscar_ciego_la_primera_vez(sesion, usuario_id, partida_id):
        llamadas.append(partida_id)
        return None if len(llamadas) == 1 else buscar_real(sesion, usuario_id, partida_id)

    monkeypatch.setattr(servicio_calibracion, "_buscar_calibracion", buscar_ciego_la_primera_vez)

    respuesta = registrar_calibracion(db, usuario, "p1", _resumen(10.0))

    assert respuesta["motivo"] == "ya_registrada"
    assert respuesta["precision_partida"] == 60.0
    assert contar_calibraciones(db, usuario.id) == 1


def test_precision_para_alcanzar_nivel_es_el_minimo_exacto() -> None:
    minimas = [precision_para_alcanzar_nivel(nivel) for nivel in range(1, 21)]

    assert precision_para_alcanzar_nivel(0) == 0.0
    assert minimas == sorted(minimas)
    assert len(set(minimas)) == 20
    for nivel, minima in enumerate(minimas, start=1):
        assert calcular_rango_desde_precision(minima)[0] >= nivel
        assert calcular_rango_desde_precision(round(minima - 0.1, 1))[0] < nivel


def test_precision_para_alcanzar_un_nivel_inalcanzable_falla() -> None:
    with pytest.raises(ValueError):
        precision_para_alcanzar_nivel(21)


def test_escala_de_niveles_sale_de_las_constantes_del_sistema() -> None:
    escala = escala_niveles()

    assert escala == {
        "nivel_min": 0,
        "nivel_max": 20,
        "nivel_max_modelo": NIVEL_MAX_MODELO,
        "bandas": {
            "Principiante": [0, 6],
            "Intermedio": [7, 13],
            "Avanzado": [14, 20],
        },
    }
    assert escala["nivel_max_modelo"] == 18
    assert {rango: tuple(banda) for rango, banda in escala["bandas"].items()} == BANDA_NIVEL_POR_RANGO


def test_estado_nivel_de_un_jugador_sin_calibraciones(db) -> None:
    estado = estado_nivel_jugador(db, _usuario(db))

    assert estado["nivel_estimado"] is None
    assert estado["rango_estimado"] is None
    assert estado["diagnostico_completado"] is False
    assert estado["partidas_calibradas"] == 0
    assert estado["precision_promedio"] is None
    assert estado["progreso_siguiente_nivel"] is None
    assert estado["precision_siguiente_nivel"] is None
    assert estado["calibraciones"] == []
    assert estado["escala"] == escala_niveles()


def test_estado_nivel_con_nivel_manual_pero_sin_calibraciones_da_la_meta_sin_progreso(db) -> None:
    usuario = _usuario(db)
    actualizar_nivel_estimado(db, usuario, 5, "Principiante")

    estado = estado_nivel_jugador(db, usuario)

    assert estado["diagnostico_completado"] is False
    assert estado["progreso_siguiente_nivel"] is None
    assert estado["precision_siguiente_nivel"] == precision_para_alcanzar_nivel(6)


def test_estado_nivel_con_calibraciones_calcula_promedio_y_progreso(db) -> None:
    usuario = _usuario(db)
    for i, precision in enumerate([40.0, 50.0, 60.0]):
        registrar_calibracion(db, usuario, f"p{i}", _resumen(precision))

    estado = estado_nivel_jugador(db, usuario)

    nivel, rango = calcular_rango_desde_precision(50.0)
    piso = precision_para_alcanzar_nivel(nivel)
    meta = precision_para_alcanzar_nivel(nivel + 1)
    assert (estado["nivel_estimado"], estado["rango_estimado"]) == (nivel, rango)
    assert estado["diagnostico_completado"] is True
    assert estado["partidas_calibradas"] == 3
    assert estado["precision_promedio"] == 50.0
    assert estado["precision_siguiente_nivel"] == meta
    assert estado["progreso_siguiente_nivel"] == pytest.approx((50.0 - piso) / (meta - piso), abs=0.001)
    assert 0.0 <= estado["progreso_siguiente_nivel"] <= 1.0
    assert [c["partida_id"] for c in estado["calibraciones"]] == ["p0", "p1", "p2"]
    assert [c["precision"] for c in estado["calibraciones"]] == [40.0, 50.0, 60.0]
    assert set(estado["calibraciones"][0]) == {"partida_id", "precision", "nivel", "rango", "creado_en"}
    assert estado["calibraciones"][0]["nivel"] == calcular_rango_desde_precision(40.0)[0]
    assert isinstance(estado["calibraciones"][0]["creado_en"], str)


def test_estado_nivel_devuelve_solo_las_ultimas_diez_en_orden_cronologico(db) -> None:
    usuario = _usuario(db)
    for i in range(MAX_CALIBRACIONES_HISTORIAL + 2):
        registrar_calibracion(db, usuario, f"p{i}", _resumen(50.0))

    estado = estado_nivel_jugador(db, usuario)

    assert estado["partidas_calibradas"] == MAX_CALIBRACIONES_HISTORIAL + 2
    assert [c["partida_id"] for c in estado["calibraciones"]] == [f"p{i}" for i in range(2, 12)]


def test_estado_nivel_en_el_nivel_maximo_no_tiene_siguiente(db) -> None:
    usuario = _usuario(db)
    registrar_calibracion(db, usuario, "p1", _resumen(100.0))

    estado = estado_nivel_jugador(db, usuario)

    assert estado["nivel_estimado"] == 20
    assert estado["progreso_siguiente_nivel"] is None
    assert estado["precision_siguiente_nivel"] is None


def test_contar_calibraciones_por_usuario_agrupa_en_una_consulta(db) -> None:
    ana = _usuario(db, email="ana@test.com")
    beto = _usuario(db, email="beto@test.com")
    sin_partidas = _usuario(db, email="cami@test.com")
    registrar_calibracion(db, ana, "a1", _resumen(50.0))
    registrar_calibracion(db, ana, "a2", _resumen(50.0))
    registrar_calibracion(db, beto, "b1", _resumen(50.0))

    conteos = contar_calibraciones_por_usuario(db, [ana.id, beto.id, sin_partidas.id])

    assert conteos == {ana.id: 2, beto.id: 1}
    assert contar_calibraciones_por_usuario(db, []) == {}


def test_la_restriccion_unica_esta_en_la_tabla(db) -> None:
    usuario = _usuario(db)
    registrar_calibracion(db, usuario, "p1", _resumen(50.0))

    filas = db.scalar(select(func.count()).select_from(CalibracionORM).where(CalibracionORM.partida_id == "p1"))

    assert filas == 1
    restricciones = {c.name for c in CalibracionORM.__table__.constraints}
    assert "uq_calibracion_usuario_partida" in restricciones
