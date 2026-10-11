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


def test_progreso_semanal_devuelve_siempre_ocho_semanas_de_la_mas_vieja_a_la_actual() -> None:
    from datetime import date

    from backend.servicios.usuario.servicio_estadisticas import armar_progreso_semanal

    hoy = date(2026, 10, 14)  # miércoles; su semana arranca el lunes 12
    semanas = armar_progreso_semanal([], [], hoy)

    assert len(semanas) == 8
    assert semanas[-1]["semana_inicio"] == "2026-10-12"
    assert semanas[0]["semana_inicio"] == "2026-08-24"
    # Sin datos no se inventa precisión: queda vacía, no en 0 %.
    assert all(s["partidas"] == 0 and s["precision"] is None for s in semanas)


def test_progreso_semanal_agrupa_partidas_victorias_y_precision_por_semana() -> None:
    from datetime import date

    from backend.servicios.usuario.servicio_estadisticas import armar_progreso_semanal

    hoy = date(2026, 10, 14)
    partidas = [
        (date(2026, 10, 12), "1-0"),  # esta semana, victoria
        (date(2026, 10, 14), "0-1"),  # esta semana, derrota
        (date(2026, 10, 5), "1-0"),  # semana anterior
    ]
    jugadas = [
        (date(2026, 10, 13), 10),  # acierto (pérdida <= 50)
        (date(2026, 10, 13), 40),  # acierto
        (date(2026, 10, 14), 120),  # error
    ]

    semanas = {s["semana_inicio"]: s for s in armar_progreso_semanal(partidas, jugadas, hoy)}

    actual = semanas["2026-10-12"]
    assert (actual["partidas"], actual["victorias"]) == (2, 1)
    assert actual["precision"] == 66.7
    anterior = semanas["2026-10-05"]
    assert (anterior["partidas"], anterior["victorias"], anterior["precision"]) == (1, 1, None)


def test_progreso_semanal_ignora_lo_que_cae_fuera_de_las_ocho_semanas() -> None:
    from datetime import date

    from backend.servicios.usuario.servicio_estadisticas import armar_progreso_semanal

    semanas = armar_progreso_semanal([(date(2026, 1, 5), "1-0")], [(date(2026, 1, 5), 0)], date(2026, 10, 14))

    assert sum(s["partidas"] for s in semanas) == 0


def test_clasificar_fase_separa_apertura_medio_juego_y_final() -> None:
    from backend.servicios.usuario.servicio_estadisticas import clasificar_fase

    assert clasificar_fase(1) == "apertura"
    assert clasificar_fase(20) == "apertura"
    assert clasificar_fase(21) == "medio"
    assert clasificar_fase(60) == "medio"
    assert clasificar_fase(61) == "final"


def test_precision_por_fase_calcula_cada_fase_y_deja_vacia_la_que_no_tiene_jugadas() -> None:
    from backend.servicios.usuario.servicio_estadisticas import armar_precision_por_fase

    fases = {f["fase"]: f for f in armar_precision_por_fase([(1, 0), (3, 30), (5, 200), (30, 10)])}

    assert (fases["apertura"]["jugadas"], fases["apertura"]["precision"]) == (3, 66.7)
    assert (fases["medio"]["jugadas"], fases["medio"]["precision"]) == (1, 100.0)
    assert (fases["final"]["jugadas"], fases["final"]["precision"]) == (0, None)
