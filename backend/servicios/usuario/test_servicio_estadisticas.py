from backend.servicios.usuario.servicio_estadisticas import _clasificar_jugada, _perdida


def test_perdida_devuelve_la_diferencia_de_puntaje() -> None:
    assert _perdida(evaluacion_cp=-100, evaluacion_mejor_cp=50, mate_en=None, mate_en_mejor=None) == 150


def test_perdida_es_none_sin_evaluacion_de_la_jugada_jugada() -> None:
    assert _perdida(evaluacion_cp=None, evaluacion_mejor_cp=50, mate_en=None, mate_en_mejor=None) is None


def test_perdida_es_none_sin_evaluacion_de_la_mejor_jugada() -> None:
    assert _perdida(evaluacion_cp=-100, evaluacion_mejor_cp=None, mate_en=None, mate_en_mejor=None) is None


def test_perdida_cuenta_mate_perdido_a_favor_como_perdida_enorme() -> None:
    """Había mate en 1 a favor y la jugada real solo vale 50 cp → pérdida máxima."""
    perdida = _perdida(
        evaluacion_cp=50, evaluacion_mejor_cp=None, mate_en=None, mate_en_mejor=1
    )
    assert perdida is not None and perdida > 50_000


def test_clasifica_blunder_por_perdida_de_centipawns() -> None:
    assert _clasificar_jugada(evaluacion_cp=-400, evaluacion_mejor_cp=0, mate_en=None, mate_en_mejor=None) == "blunder"


def test_clasifica_error_por_perdida_de_centipawns() -> None:
    assert _clasificar_jugada(evaluacion_cp=-150, evaluacion_mejor_cp=0, mate_en=None, mate_en_mejor=None) == "error"


def test_clasifica_inexactitud_por_perdida_de_centipawns() -> None:
    assert _clasificar_jugada(evaluacion_cp=-70, evaluacion_mejor_cp=0, mate_en=None, mate_en_mejor=None) == "inexactitud"


def test_no_clasifica_jugada_con_perdida_menor_a_50() -> None:
    assert _clasificar_jugada(evaluacion_cp=-10, evaluacion_mejor_cp=0, mate_en=None, mate_en_mejor=None) is None


def test_clasifica_blunder_si_se_perdio_un_mate_a_favor() -> None:
    """Había mate en 1 a favor del jugador y no se jugó — blunder aunque la
    jugada real todavía tenga una evaluación en cp aceptable."""
    assert _clasificar_jugada(
        evaluacion_cp=50, evaluacion_mejor_cp=None, mate_en=None, mate_en_mejor=1
    ) == "blunder"


def test_clasifica_blunder_si_la_jugada_lleva_a_que_lo_maten() -> None:
    """La mejor jugada no tenía mate forzado disponible, pero la jugada real
    dejó mate en contra — blunder aunque `evaluacion_mejor_cp` sea moderada."""
    assert _clasificar_jugada(
        evaluacion_cp=None, evaluacion_mejor_cp=-100, mate_en=-1, mate_en_mejor=None
    ) == "blunder"


def test_no_clasifica_sin_evaluacion_de_la_jugada_realmente_jugada() -> None:
    assert _clasificar_jugada(evaluacion_cp=None, evaluacion_mejor_cp=0, mate_en=None, mate_en_mejor=None) is None


def test_no_clasifica_sin_evaluacion_de_la_mejor_jugada() -> None:
    assert _clasificar_jugada(evaluacion_cp=-400, evaluacion_mejor_cp=None, mate_en=None, mate_en_mejor=None) is None
