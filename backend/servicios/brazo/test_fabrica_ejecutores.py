import pytest

from backend.servicios.brazo.ejecutor_movimiento import EjecutorReal
from backend.servicios.brazo.fabrica_ejecutores import crear_ejecutor_movimiento

HOST_DOCUMENTACION = "192.0.2.1"


def test_crear_ejecutor_movimiento_devuelve_la_clase_correcta_por_modo():
    pytest.importorskip("pybullet")
    from backend.servicios.brazo.ejecutor_movimiento import EjecutorSimulado

    ejecutor_simulado = crear_ejecutor_movimiento("simulado", modo_gui=False)
    try:
        assert isinstance(ejecutor_simulado, EjecutorSimulado)
    finally:
        ejecutor_simulado.cerrar()

    ejecutor_real = crear_ejecutor_movimiento("real", host=HOST_DOCUMENTACION)
    assert isinstance(ejecutor_real, EjecutorReal)


def test_crear_ejecutor_movimiento_tipo_no_soportado_lanza_error():
    with pytest.raises(ValueError):
        crear_ejecutor_movimiento("invalido")
