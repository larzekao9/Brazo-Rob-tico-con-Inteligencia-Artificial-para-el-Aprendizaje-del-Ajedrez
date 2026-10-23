import chess
import pytest

from backend.servicios.vision import captura_estable
from backend.servicios.vision.test_jugada_probable import INICIAL, OCUPACION, PIEZAS, _lectura_de, _tras
from backend.servicios.vision.validacion_posicion import comparar_con_esperada, material_imposible, problemas_de_posicion


def test_la_posicion_inicial_bien_puesta_coincide() -> None:
    resultado = comparar_con_esperada(INICIAL, [_lectura_de(chess.Board(), OCUPACION)])

    assert resultado == {"estado": "coincide", "coinciden": 64, "total": 64, "discrepancias": [], "avisos_tipo": []}


def test_una_pieza_movida_deja_la_posicion_casi_y_nombra_las_casillas() -> None:
    resultado = comparar_con_esperada(INICIAL, [_lectura_de(_tras(INICIAL, "e2e4"), OCUPACION)])

    assert resultado["estado"] == "casi" and resultado["coinciden"] == 62
    assert {d["casilla"] for d in resultado["discrepancias"]} == {"e2", "e4"}
    assert {d["casilla"]: d["vista"] for d in resultado["discrepancias"]} == {"e2": "vacia", "e4": "blanca"}


def test_varias_piezas_fuera_de_lugar_no_coinciden() -> None:
    visto = _tras(_tras(INICIAL, "e2e4").fen(), "d7d5")
    visto.push_uci("b1c3")

    assert comparar_con_esperada(INICIAL, [_lectura_de(visto, OCUPACION)])["estado"] == "no_coincide"


def test_el_tipo_de_pieza_equivocado_es_solo_un_aviso_si_la_ocupacion_esta_bien() -> None:
    visto = chess.Board()
    visto.set_piece_at(chess.A1, chess.Piece(chess.KNIGHT, chess.WHITE))  # la torre de a1 se lee como caballo
    resultado = comparar_con_esperada(INICIAL, [_lectura_de(chess.Board(), OCUPACION), _lectura_de(visto, PIEZAS)])

    assert resultado["estado"] == "coincide"
    assert [a["casilla"] for a in resultado["avisos_tipo"]] == ["a1"]
    assert resultado["avisos_tipo"][0]["esperada"] == "white-rook" and resultado["avisos_tipo"][0]["vista"] == "white-knight"


def test_sin_lectura_de_ocupacion_no_se_puede_comparar() -> None:
    with pytest.raises(ValueError):
        comparar_con_esperada(INICIAL, [_lectura_de(chess.Board(), PIEZAS)])


def test_posicion_inicial_y_posiciones_normales_no_tienen_problemas() -> None:
    assert problemas_de_posicion(INICIAL) == []
    assert problemas_de_posicion("8/P6k/8/8/8/8/8/4K3 w - - 0 1") == []


def test_posiciones_imposibles_se_detectan() -> None:
    assert "Falta el rey negro" in problemas_de_posicion("8/8/8/8/8/8/8/4K3 w - - 0 1")
    assert any("coronaciones" in p for p in problemas_de_posicion("4k3/8/8/8/8/8/PPPPPPPP/QQQQKQQQ w - - 0 1"))
    assert any("peones" in p for p in problemas_de_posicion("P3k3/8/8/8/8/8/8/4K3 w - - 0 1"))


def test_el_material_no_puede_aparecer_de_la_nada_pero_si_por_coronacion() -> None:
    coronada = "rnbqkbnr/1ppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # un peón negro menos...
    assert material_imposible(INICIAL, coronada) == []  # ...solo bajó el material
    assert any("piezas blancas" in p for p in material_imposible(INICIAL, "rnbqkbnr/pppppppp/Q7/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"))
    assert material_imposible("8/P6k/8/8/8/8/8/4K3 w - - 0 1", "Q7/7k/8/8/8/8/8/4K3 b - - 0 1") == []


def test_camaras_a_usar_filtra_por_las_calibradas(monkeypatch) -> None:
    monkeypatch.setattr(captura_estable, "camaras_calibradas", lambda: ["principal", "secundaria"])

    assert captura_estable.camaras_a_usar(None) == ["principal", "secundaria"]
    assert captura_estable.camaras_a_usar(["secundaria"]) == ["secundaria"]
    monkeypatch.setattr(captura_estable, "camaras_calibradas", lambda: ["principal"])
    assert captura_estable.camaras_a_usar(["principal", "secundaria"]) == ["principal"]
    with pytest.raises(ValueError, match="calibrada"):
        captura_estable.camaras_a_usar(["secundaria"])


def _probs(asignadas: dict[int, tuple[str, float, str]]):
    """Matriz `(64, 13)`: cada fila vacía, salvo las dadas `{fila: (clase vista, confianza, segunda opción)}`."""
    import numpy as np

    from backend.servicios.vision.modelo_piezas import CLASES

    probs = np.full((64, len(CLASES)), 0.001)
    probs[:, CLASES.index("vacia")] = 0.99
    for fila, (clase, confianza, segunda) in asignadas.items():
        probs[fila] = 0.001
        probs[fila, CLASES.index(clase)] = confianza
        probs[fila, CLASES.index(segunda)] = 1 - confianza - 0.012
    return probs


def _clases_vistas(probs) -> list[str]:
    from backend.servicios.vision.modelo_piezas import CLASES

    return [CLASES[i] for i in probs.argmax(axis=1)]


def test_tres_reyes_blancos_se_corrigen_dejando_el_mas_seguro() -> None:
    from backend.servicios.vision.modelo_piezas import CLASES
    from backend.servicios.vision.validacion_posicion import limitar_por_material

    probs = _probs({56: ("white-king", 0.9, "white-rook"), 57: ("white-king", 0.8, "white-rook"), 58: ("white-king", 0.55, "white-queen")})
    vistas = _clases_vistas(limitar_por_material(probs, list(CLASES)))

    assert vistas[56] == "white-king"  # el más seguro se queda
    assert vistas[57] == "white-rook" and vistas[58] == "white-queen"  # los otros bajan a su segunda opción
    assert vistas.count("white-king") == 1


def test_un_tercer_alfil_solo_se_acepta_si_falta_un_peon_que_lo_explique() -> None:
    from backend.servicios.vision.modelo_piezas import CLASES
    from backend.servicios.vision.validacion_posicion import limitar_por_material

    peones = {fila: ("white-pawn", 0.95, "vacia") for fila in range(8, 16)}
    # c1 y d2 son casillas oscuras y f1 clara: el tercero sobra en las oscuras (un alfil nunca cambia de color de casilla).
    tres_alfiles = {58: ("white-bishop", 0.9, "white-knight"), 61: ("white-bishop", 0.6, "white-knight"), 51: ("white-bishop", 0.7, "white-knight")}

    con_8_peones = _clases_vistas(limitar_por_material(_probs({**peones, **tres_alfiles}), list(CLASES)))
    con_7_peones = _clases_vistas(limitar_por_material(_probs({**{f: v for f, v in peones.items() if f != 8}, **tres_alfiles}), list(CLASES)))

    assert con_8_peones.count("white-bishop") == 2 and con_8_peones[51] == "white-knight"  # cede el menos seguro de los del mismo color
    assert con_8_peones[61] == "white-bishop"  # el de casilla clara es legal aunque sea el menos seguro de los tres
    assert con_7_peones.count("white-bishop") == 3  # un peón coronó: es posible


def test_limitar_no_toca_lecturas_de_ocupacion_ni_posiciones_posibles() -> None:
    import numpy as np

    from backend.servicios.vision.modelo_piezas import CLASES
    from backend.servicios.vision.validacion_posicion import limitar_por_material

    ocupacion = np.full((64, 3), 1 / 3)
    assert limitar_por_material(ocupacion, ["vacia", "blanca", "negra"]) is ocupacion
    posible = _probs({4: ("black-king", 0.9, "black-queen"), 60: ("white-king", 0.9, "white-queen")})
    assert np.allclose(limitar_por_material(posible, list(CLASES)), posible)


def test_dos_alfiles_en_casillas_del_mismo_color_sin_peones_que_falten() -> None:
    from backend.servicios.vision.modelo_piezas import CLASES
    from backend.servicios.vision.validacion_posicion import casilla_oscura, limitar_por_material

    assert casilla_oscura("a1") and not casilla_oscura("b1") and casilla_oscura("h8")
    peones = {fila: ("black-pawn", 0.95, "vacia") for fila in range(8, 16)}
    dos_claros = {2: ("black-bishop", 0.9, "black-knight"), 5: ("black-bishop", 0.65, "black-knight")}  # c8 y f8: c8 es clara, f8 oscura
    vistas = _clases_vistas(limitar_por_material(_probs({**peones, **dos_claros}), list(CLASES)))
    assert vistas.count("black-bishop") == 2  # c8 y f8 son de distinto color: la posición inicial es legal
    mismo_color = {2: ("black-bishop", 0.9, "black-knight"), 4: ("black-bishop", 0.65, "black-knight")}  # c8 y e8, las dos claras
    vistas = _clases_vistas(limitar_por_material(_probs({**peones, **mismo_color}), list(CLASES)))
    assert vistas[2] == "black-bishop" and vistas[4] == "black-knight"


def test_un_peon_en_la_primera_o_la_ultima_fila_pasa_a_su_segunda_opcion() -> None:
    from backend.servicios.vision.modelo_piezas import CLASES
    from backend.servicios.vision.validacion_posicion import limitar_por_material

    probs = _probs({7: ("white-pawn", 0.7, "white-queen"), 56: ("black-pawn", 0.8, "vacia"), 20: ("white-pawn", 0.9, "vacia")})  # h8, a1, e6
    vistas = _clases_vistas(limitar_por_material(probs, list(CLASES)))
    assert vistas[7] == "white-queen" and vistas[56] == "vacia" and vistas[20] == "white-pawn"


def test_problemas_de_piezas_sin_turno_y_sin_exigir_reyes() -> None:
    from backend.servicios.vision.validacion_posicion import problemas_de_piezas

    assert problemas_de_piezas("8/8/8/8/4P3/8/8/8") == []  # un peón suelto: al probar piezas no hace falta que estén los reyes
    assert any("rey" in p for p in problemas_de_piezas("8/8/8/8/4P3/8/8/8", exigir_reyes=True))
    assert problemas_de_piezas("4k2P/8/8/8/8/8/8/4K3") == ["Hay peones en la primera o en la última fila"]
    assert any("coronaciones" in p for p in problemas_de_piezas("4k3/pppppppp/8/8/8/8/8/2b1Kb1b"))  # tres alfiles negros con 8 peones
    assert problemas_de_piezas("4k3/8/8/8/8/8/8/4KQ2") == []  # jaque al rey negro: posible si le toca a las negras
    with pytest.raises(ValueError):
        problemas_de_piezas("esto no es un fen")
