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


def test_resumir_turing_por_nivel_agrupa_y_mide_precision() -> None:
    from backend.servicios.usuario.servicio_estadisticas import resumir_turing_por_nivel

    # Nivel 8: dos partidas; una jugada perfecta (0 de pérdida), una con 120 cp de pérdida y otra sin evaluar.
    filas = [
        (8, "p1", 10, 10, None, None),
        (8, "p1", -50, -50, None, None),
        (8, "p2", -130, -10, None, None),
        (8, "p2", None, None, None, None),
        (14, "p3", 0, 0, None, None),
    ]
    niveles = {n["nivel"]: n for n in resumir_turing_por_nivel(filas)}
    assert niveles[8]["partidas_analizadas"] == 2
    assert niveles[8]["jugadas_analizadas"] == 3
    assert niveles[8]["precision"] == round(2 / 3 * 100, 1)
    assert niveles[8]["blunders"] == 0
    assert niveles[14]["jugadas_analizadas"] == 1


def test_resumir_turing_por_nivel_no_deja_que_un_mate_distorsione_la_perdida_media() -> None:
    from backend.servicios.usuario.servicio_estadisticas import resumir_turing_por_nivel

    filas = [
        (5, "p1", 0, 0, None, None),
        (5, "p1", -100000, 0, -3, None),  # mate en contra: pérdida enorme
    ]
    nivel = resumir_turing_por_nivel(filas)[0]
    assert nivel["perdida_media_cp"] <= 1000
