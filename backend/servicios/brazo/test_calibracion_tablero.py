import pytest

from backend.servicios.brazo.calibracion_tablero import (
    PuntoCalibracion,
    calcular_posiciones_casillas,
)


def test_calcular_posiciones_casillas_reconstruye_casilla_intermedia_con_grilla_sintetica():
    puntos = [
        PuntoCalibracion(casilla="a1", x=0.0, y=0.0, z=10.0),
        PuntoCalibracion(casilla="h1", x=700.0, y=0.0, z=10.0),
        PuntoCalibracion(casilla="a8", x=0.0, y=700.0, z=10.0),
    ]

    posiciones = calcular_posiciones_casillas(puntos)

    assert len(posiciones) == 64
    x, y, z = posiciones["e5"]
    assert x == pytest.approx(400.0)
    assert y == pytest.approx(400.0)
    assert z == pytest.approx(10.0)


def test_calcular_posiciones_casillas_menos_de_3_puntos_lanza_error():
    with pytest.raises(ValueError):
        calcular_posiciones_casillas([PuntoCalibracion(casilla="a1", x=0.0, y=0.0, z=10.0)])
