import pytest

pytest.importorskip("pybullet")
from backend.servicios.simulacion.ver_partida_en_vivo import (
    _elegir_id_mas_reciente_sin_terminar,
)


def test_elige_id_mas_reciente_entre_las_no_terminadas():
    partidas = [
        {"id": "vieja", "terminada": False, "creada_en": "2026-01-01T10:00:00"},
        {"id": "terminada-reciente", "terminada": True, "creada_en": "2026-01-03T10:00:00"},
        {"id": "nueva", "terminada": False, "creada_en": "2026-01-02T10:00:00"},
    ]

    assert _elegir_id_mas_reciente_sin_terminar(partidas) == "nueva"


def test_elige_lanza_systemexit_si_no_hay_partidas_sin_terminar():
    partidas = [{"id": "a", "terminada": True, "creada_en": "2026-01-01T10:00:00"}]

    with pytest.raises(SystemExit):
        _elegir_id_mas_reciente_sin_terminar(partidas)


def test_elige_lanza_systemexit_si_lista_vacia():
    with pytest.raises(SystemExit):
        _elegir_id_mas_reciente_sin_terminar([])
