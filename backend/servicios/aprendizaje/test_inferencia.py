"""Test de inferencia (HU4) — no depende del checkpoint real (26MB, vive en
`training/checkpoints/`, ignorado por git): genera uno chico con pesos sin
entrenar para probar que `cargar_modelo`/`predecir_jugada` funcionan de punta
a punta. La precisión del modelo real se evalúa aparte (ver `docs/plan_sprints.md`).

Se salta automáticamente si `torch` no está instalado (ver test_modelo_jugadas.py).
"""
import random
from collections import Counter

import chess
import pytest

torch = pytest.importorskip("torch")

from backend.servicios.aprendizaje import inferencia  # noqa: E402
from backend.servicios.aprendizaje.inferencia import (
    cargar_modelo,
    explicar_top_candidatas,
    predecir_jugada,
    predecir_jugada_maestra,
    predecir_top_jugadas,
    calcular_atencion,
    calcular_saliencia,
    estado_modelo,
    temperatura_y_pool_por_nivel,
)  # noqa: E402
from backend.servicios.aprendizaje.modelo_jugadas import (
    NUM_CLASES,
    RedPrediccionJugadas,
    RedResNetAjedrez,
    RedSEResNetAjedrez,
)  # noqa: E402
from training.data_pipeline import jugada_a_etiqueta  # noqa: E402


@pytest.fixture
def checkpoint_de_prueba(tmp_path):
    ruta = tmp_path / "checkpoint_prueba.pt"
    torch.save({"state_dict": RedPrediccionJugadas().state_dict(), "num_clases": NUM_CLASES}, ruta)
    return ruta


@pytest.fixture
def checkpoint_resnet_de_prueba(tmp_path):
    ruta = tmp_path / "checkpoint_resnet_prueba.pt"
    torch.save(
        {
            "state_dict": RedResNetAjedrez(canales=64, cantidad_bloques=2).state_dict(),
            "num_clases": NUM_CLASES,
            "arquitectura": "resnet",
        },
        ruta,
    )
    return ruta


@pytest.fixture
def checkpoint_se_resnet_de_prueba(tmp_path):
    ruta = tmp_path / "checkpoint_se_resnet_prueba.pt"
    torch.save(
        {
            "state_dict": RedSEResNetAjedrez(canales=64, cantidad_bloques=2).state_dict(),
            "num_clases": NUM_CLASES,
            "arquitectura": "se_resnet",
        },
        ruta,
    )
    return ruta


def test_cargar_modelo_devuelve_red_en_modo_eval(checkpoint_de_prueba):
    modelo = cargar_modelo(checkpoint_de_prueba)
    assert isinstance(modelo, RedPrediccionJugadas)
    assert not modelo.training


def test_cargar_modelo_detecta_y_soporta_resnet(checkpoint_resnet_de_prueba):
    modelo = cargar_modelo(checkpoint_resnet_de_prueba)
    assert isinstance(modelo, RedResNetAjedrez)
    assert not modelo.training


def test_cargar_modelo_detecta_y_soporta_se_resnet(checkpoint_se_resnet_de_prueba):
    modelo = cargar_modelo(checkpoint_se_resnet_de_prueba)
    assert isinstance(modelo, RedSEResNetAjedrez)
    assert not modelo.training




def test_predecir_jugada_devuelve_una_jugada_legal(checkpoint_de_prueba):
    tablero = chess.Board()
    jugada = predecir_jugada(tablero.fen(), checkpoint_de_prueba)
    assert jugada in [tablero.san(m) for m in tablero.legal_moves]


def test_predecir_jugada_maestra_devuelve_jugada_legal(checkpoint_de_prueba):
    tablero = chess.Board()
    jugada = predecir_jugada_maestra(tablero.fen(), checkpoint_de_prueba)
    assert jugada in [tablero.san(m) for m in tablero.legal_moves]


def test_predecir_jugada_sin_jugadas_legales_falla(checkpoint_de_prueba):
    fen_ahogado = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    with pytest.raises(ValueError):
        predecir_jugada(fen_ahogado, checkpoint_de_prueba)


def test_predecir_jugada_maestra_sin_jugadas_legales_falla(checkpoint_de_prueba):
    fen_ahogado = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    with pytest.raises(ValueError):
        predecir_jugada_maestra(fen_ahogado, checkpoint_de_prueba)


def test_explicar_top_candidatas_devuelve_cantidad_correcta(checkpoint_de_prueba):
    tablero = chess.Board()
    candidatas = explicar_top_candidatas(tablero.fen(), checkpoint_de_prueba, top_candidatas=3)
    assert len(candidatas) == 3


def test_explicar_top_candidatas_respeta_top_candidatas_menor_a_jugadas_legales(checkpoint_de_prueba):
    tablero = chess.Board()
    candidatas = explicar_top_candidatas(tablero.fen(), checkpoint_de_prueba, top_candidatas=1)
    assert len(candidatas) == 1
    assert candidatas[0]["elegida"] is True


def test_explicar_top_candidatas_exactamente_una_elegida(checkpoint_de_prueba):
    tablero = chess.Board()
    candidatas = explicar_top_candidatas(tablero.fen(), checkpoint_de_prueba, top_candidatas=3)
    elegidas = [c for c in candidatas if c["elegida"]]
    assert len(elegidas) == 1


def test_explicar_top_candidatas_coincide_con_predecir_jugada_maestra(checkpoint_de_prueba):
    """La candidata marcada `elegida=True` debe ser la misma jugada que
    `predecir_jugada_maestra` elige para la misma posición — backend y frontend
    nunca deberían mostrar jugadas distintas."""
    tablero = chess.Board()
    jugada_maestra = predecir_jugada_maestra(tablero.fen(), checkpoint_de_prueba)
    candidatas = explicar_top_candidatas(tablero.fen(), checkpoint_de_prueba, top_candidatas=3)
    elegida = next(c for c in candidatas if c["elegida"])
    assert elegida["jugada"] == jugada_maestra


def test_explicar_top_candidatas_probabilidades_validas(checkpoint_de_prueba):
    tablero = chess.Board()
    candidatas = explicar_top_candidatas(tablero.fen(), checkpoint_de_prueba, top_candidatas=3)
    for candidata in candidatas:
        assert 0.0 <= candidata["probabilidad"] <= 1.0
    probs = [c["probabilidad"] for c in candidatas]
    assert probs == sorted(probs, reverse=True)


def test_explicar_top_candidatas_jugadas_son_legales_y_claves_completas(checkpoint_de_prueba):
    tablero = chess.Board()
    jugadas_legales = [tablero.san(m) for m in tablero.legal_moves]
    candidatas = explicar_top_candidatas(tablero.fen(), checkpoint_de_prueba, top_candidatas=3)

    claves_esperadas = {
        "jugada", "probabilidad", "da_jaque_mate",
        "rival_tiene_mate_en_1", "pieza_colgada", "elegida",
    }
    for candidata in candidatas:
        assert candidata["jugada"] in jugadas_legales
        assert claves_esperadas <= set(candidata.keys())
        assert isinstance(candidata["da_jaque_mate"], bool)
        assert isinstance(candidata["rival_tiene_mate_en_1"], bool)
        assert isinstance(candidata["pieza_colgada"], bool)
        assert isinstance(candidata["elegida"], bool)


def test_explicar_top_candidatas_sin_jugadas_legales_falla(checkpoint_de_prueba):
    fen_ahogado = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    with pytest.raises(ValueError):
        explicar_top_candidatas(fen_ahogado, checkpoint_de_prueba)



def test_predecir_top_jugadas_devuelve_top_n_y_probabilidades_suman_uno(checkpoint_de_prueba):
    tablero = chess.Board()
    resultado = predecir_top_jugadas(tablero.fen(), top_n=3, ruta_checkpoint=checkpoint_de_prueba)

    assert len(resultado) == 3
    assert all(isinstance(j, str) and isinstance(p, float) for j, p in resultado)
    # Probabilidades son positivas y ordenadas descendente
    probs = [p for _, p in resultado]
    assert all(p > 0 for p in probs)
    assert probs == sorted(probs, reverse=True)


def test_predecir_top_jugadas_jugadas_son_legales(checkpoint_de_prueba):
    tablero = chess.Board()
    resultado = predecir_top_jugadas(tablero.fen(), top_n=5, ruta_checkpoint=checkpoint_de_prueba)
    jugadas_legales = [tablero.san(m) for m in tablero.legal_moves]

    for jugada_san, _ in resultado:
        assert jugada_san in jugadas_legales


def test_calcular_saliencia_shape_64_valores_en_0_1(checkpoint_de_prueba):
    tablero = chess.Board()
    saliencia = calcular_saliencia(tablero.fen(), ruta_checkpoint=checkpoint_de_prueba)

    assert len(saliencia) == 64
    assert all(isinstance(v, float) for v in saliencia)
    assert all(0.0 <= v <= 1.0 for v in saliencia)


def test_calcular_atencion_devuelve_un_valor_por_bloque_se(checkpoint_se_resnet_de_prueba):
    tablero = chess.Board()
    atencion = calcular_atencion(tablero.fen(), ruta_checkpoint=checkpoint_se_resnet_de_prueba)

    assert len(atencion) == 2  # checkpoint_se_resnet_de_prueba tiene cantidad_bloques=2
    assert all(isinstance(v, float) for v in atencion)
    assert all(0.0 <= v <= 1.0 for v in atencion)


def test_calcular_atencion_lista_vacia_si_arquitectura_no_tiene_se(checkpoint_de_prueba):
    tablero = chess.Board()
    atencion = calcular_atencion(tablero.fen(), ruta_checkpoint=checkpoint_de_prueba)

    assert atencion == []


def test_calcular_atencion_sin_jugadas_legales_falla(checkpoint_se_resnet_de_prueba):
    fen_ahogado = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    with pytest.raises(ValueError):
        calcular_atencion(fen_ahogado, checkpoint_se_resnet_de_prueba)


def test_estado_modelo_parsea_nombre_archivo_correctamente(tmp_path):
    # Crear checkpoint con nombre que sigue el patrón
    ruta = tmp_path / "modelo_jugadas_v5_2026-03-15.pt"
    torch.save({"state_dict": RedPrediccionJugadas().state_dict(), "num_clases": NUM_CLASES}, ruta)

    estado = estado_modelo(ruta)

    assert estado["version"] == 5
    assert estado["fecha_entrenamiento"] == "2026-03-15"
    assert estado["num_clases"] == NUM_CLASES
    assert estado["dispositivo"] in ("cpu", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")
    assert isinstance(estado["latencia_ms"], float)
    assert estado["latencia_ms"] >= 0


def test_estado_modelo_checkpoint_sin_patron_usar_defaults(tmp_path):
    # Nombre que NO sigue el patrón
    ruta = tmp_path / "otro_modelo.pt"
    torch.save({"state_dict": RedPrediccionJugadas().state_dict(), "num_clases": 2048}, ruta)

    estado = estado_modelo(ruta)

    assert estado["version"] == 0
    assert estado["fecha_entrenamiento"] == "desconocida"
    assert estado["num_clases"] == 2048


def test_funciones_propagan_filenotfound_si_no_hay_checkpoint():
    with pytest.raises(FileNotFoundError):
        predecir_top_jugadas("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ruta_checkpoint="/no/existe.pt")
    with pytest.raises(FileNotFoundError):
        calcular_saliencia("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ruta_checkpoint="/no/existe.pt")
    with pytest.raises(FileNotFoundError):
        calcular_atencion("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ruta_checkpoint="/no/existe.pt")
    with pytest.raises(FileNotFoundError):
        estado_modelo("/no/existe.pt")
    with pytest.raises(FileNotFoundError):
        explicar_top_candidatas(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ruta_checkpoint="/no/existe.pt"
        )


# --- Adaptación al nivel del jugador (predecir_jugada_maestra con `nivel`) ---------------

# Mate en 1 (Ra8#) con la torre en 3ra posición de la red, dentro del pool a cualquier nivel.
FEN_MATE_EN_1 = "6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1"
# Cualquier jugada de la torre blanca que no sea Ra8 deja mate en 1 (Rb8-b1#); Kf1/Kh1 no.
FEN_MATE_DEL_RIVAL = "1r4k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"

NIVELES_BAJOS = [0, 5, 8, 11, 14, 17]


def _modelo_falso(tablero: chess.Board, logits_por_uci: dict[str, float]):
    """Red de mentira para UNA posición: devuelve logits fijos por jugada (el resto,
    muy bajos), para controlar qué candidatas ve `predecir_jugada_maestra` sin
    depender de pesos entrenados."""
    logits = torch.full((1, NUM_CLASES), -50.0)
    for uci, valor in logits_por_uci.items():
        logits[0, jugada_a_etiqueta(tablero, chess.Move.from_uci(uci))] = valor

    def modelo(entrada):
        return logits

    return modelo


def _usar_modelo_falso(monkeypatch, tablero: chess.Board, logits_por_uci: dict[str, float]):
    modelo = _modelo_falso(tablero, logits_por_uci)
    monkeypatch.setattr(inferencia, "cargar_modelo", lambda ruta: modelo)


def test_temperatura_y_pool_por_nivel_valores_documentados():
    assert temperatura_y_pool_por_nivel(0) == (3.0, 5)
    assert temperatura_y_pool_por_nivel(5) == (3.0, 5)
    assert temperatura_y_pool_por_nivel(8) == (2.5, 5)
    assert temperatura_y_pool_por_nivel(9) == (2.33, 4)
    assert temperatura_y_pool_por_nivel(11) == (2.0, 4)
    assert temperatura_y_pool_por_nivel(13) == (1.67, 4)
    assert temperatura_y_pool_por_nivel(14) == (1.5, 3)
    assert temperatura_y_pool_por_nivel(17) == (1.0, 3)


def test_temperatura_y_pool_por_nivel_modo_maestro_sin_muestreo():
    for nivel in (None, 18, 19, 20):
        assert temperatura_y_pool_por_nivel(nivel) == (0.0, 3)


def test_temperatura_y_pool_por_nivel_recorta_fuera_de_rango():
    assert temperatura_y_pool_por_nivel(-4) == temperatura_y_pool_por_nivel(0)
    assert temperatura_y_pool_por_nivel(99) == temperatura_y_pool_por_nivel(20)


def test_temperatura_y_pool_por_nivel_es_monotono():
    """Cuanto menor el nivel, temperatura y pool nunca son menores."""
    pares = [temperatura_y_pool_por_nivel(n) for n in range(0, 18)]
    for (t_bajo, k_bajo), (t_alto, k_alto) in zip(pares, pares[1:]):
        assert t_bajo >= t_alto
        assert k_bajo >= k_alto
    assert all(t >= 1.0 for t, _ in pares)


@pytest.mark.parametrize("nivel", [None, 18, 20])
def test_nivel_maestro_es_identico_a_la_version_sin_nivel(checkpoint_de_prueba, nivel):
    """Sin nivel, o con nivel >= 18, el resultado es el mismo que llamando sin el
    argumento, y no se consume el rng."""
    fens = [
        chess.STARTING_FEN,
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        FEN_MATE_DEL_RIVAL,
        FEN_MATE_EN_1,
    ]
    for fen in fens:
        esperado = predecir_jugada_maestra(fen, checkpoint_de_prueba)
        rng = random.Random(7)
        estado_inicial = rng.getstate()
        obtenido = predecir_jugada_maestra(fen, checkpoint_de_prueba, nivel=nivel, rng=rng)
        assert obtenido == esperado
        assert rng.getstate() == estado_inicial


@pytest.mark.parametrize("nivel", [None, 18, 20])
def test_nivel_maestro_sigue_eligiendo_la_mejor_sin_mate_del_rival(monkeypatch, nivel):
    """Reproduce la lógica previa: la mejor candidata de la red deja mate en 1, así que
    se descarta y gana la siguiente (Kf1), siempre — determinista."""
    tablero = chess.Board(FEN_MATE_DEL_RIVAL)
    _usar_modelo_falso(
        monkeypatch,
        tablero,
        {"a1a7": 9.0, "a1a2": 8.0, "g1f1": 5.0, "g1h1": 4.0},
    )
    resultados = {predecir_jugada_maestra(FEN_MATE_DEL_RIVAL, nivel=nivel) for _ in range(20)}
    assert resultados == {"Kf1"}
    assert predecir_jugada_maestra(FEN_MATE_DEL_RIVAL) == "Kf1"


def test_nivel_bajo_devuelve_jugadas_distintas_de_la_mejor_y_siempre_legales(monkeypatch):
    tablero = chess.Board()
    _usar_modelo_falso(
        monkeypatch,
        tablero,
        {"e2e4": 5.0, "d2d4": 4.5, "g1f3": 4.2, "c2c4": 4.0, "g2g3": 3.5, "b2b3": 3.0},
    )
    legales = {tablero.san(m) for m in tablero.legal_moves}
    rng = random.Random(1234)

    elegidas = Counter(
        predecir_jugada_maestra(tablero.fen(), nivel=5, rng=rng) for _ in range(1000)
    )

    assert set(elegidas) <= legales
    assert set(elegidas) - {"e4"}, "a nivel bajo debe jugar algo distinto de la mejor"
    # El pool a nivel 5 es de 5 candidatas: la 6ta de la red (b3) nunca aparece.
    assert set(elegidas) == {"e4", "d4", "Nf3", "c4", "g3"}
    # Sigue siendo razonable: la mejor de la red se juega bastante más que la 5ta.
    assert elegidas["e4"] > elegidas["g3"]


def test_nivel_bajo_juega_mas_alocado_que_nivel_alto(monkeypatch):
    tablero = chess.Board()
    _usar_modelo_falso(
        monkeypatch,
        tablero,
        {"e2e4": 5.0, "d2d4": 4.5, "g1f3": 4.2, "c2c4": 4.0, "g2g3": 3.5},
    )

    def frecuencia_de_la_mejor(nivel: int) -> float:
        rng = random.Random(99)
        jugadas = [predecir_jugada_maestra(tablero.fen(), nivel=nivel, rng=rng) for _ in range(1000)]
        return jugadas.count("e4") / len(jugadas)

    assert frecuencia_de_la_mejor(0) < frecuencia_de_la_mejor(11) < frecuencia_de_la_mejor(17)
    assert frecuencia_de_la_mejor(17) < 1.0


def test_muestreo_es_reproducible_con_la_misma_semilla(monkeypatch):
    tablero = chess.Board()
    _usar_modelo_falso(
        monkeypatch, tablero, {"e2e4": 5.0, "d2d4": 4.5, "g1f3": 4.2, "c2c4": 4.0, "g2g3": 3.5}
    )
    primera = [predecir_jugada_maestra(tablero.fen(), nivel=3, rng=random.Random(5)) for _ in range(3)]
    segunda = [predecir_jugada_maestra(tablero.fen(), nivel=3, rng=random.Random(5)) for _ in range(3)]
    assert primera == segunda


@pytest.mark.parametrize("nivel", NIVELES_BAJOS)
def test_nivel_bajo_siempre_juega_el_mate_en_1_si_esta_entre_las_candidatas(monkeypatch, nivel):
    tablero = chess.Board(FEN_MATE_EN_1)
    _usar_modelo_falso(
        monkeypatch,
        tablero,
        {"e1d1": 5.0, "e1d2": 4.8, "a1a8": 4.6, "e1e2": 4.4, "a1b1": 4.2},
    )
    esperado = tablero.san(chess.Move.from_uci("a1a8"))
    assert esperado == "Ra8#"

    for semilla in range(40):
        rng = random.Random(semilla)
        assert predecir_jugada_maestra(FEN_MATE_EN_1, nivel=nivel, rng=rng) == esperado


@pytest.mark.parametrize("nivel", NIVELES_BAJOS)
def test_nivel_bajo_nunca_juega_una_jugada_que_permite_mate_en_1(monkeypatch, nivel):
    tablero = chess.Board(FEN_MATE_DEL_RIVAL)
    peligrosas = ["a1a7", "a1a2", "a1a3"]
    seguras = ["g1f1", "g1h1"]
    # Orden de la red: peligrosa, segura, segura, peligrosa, peligrosa. Las dos seguras
    # entran en el pool de cualquier nivel < 18 (tamaño 3 a 5).
    _usar_modelo_falso(
        monkeypatch,
        tablero,
        {"a1a7": 9.0, "g1f1": 8.0, "g1h1": 7.9, "a1a2": 7.0, "a1a3": 6.0},
    )
    # Precondición del escenario: las jugadas "peligrosas" de verdad permiten mate en 1.
    for uci in peligrosas:
        assert inferencia._evaluar_candidata_tactica(tablero, chess.Move.from_uci(uci))["rival_tiene_mate_en_1"]
    for uci in seguras:
        assert not inferencia._evaluar_candidata_tactica(tablero, chess.Move.from_uci(uci))["rival_tiene_mate_en_1"]

    permitidas = {tablero.san(chess.Move.from_uci(u)) for u in seguras}
    rng = random.Random(2024)
    elegidas = Counter(predecir_jugada_maestra(FEN_MATE_DEL_RIVAL, nivel=nivel, rng=rng) for _ in range(300))

    assert set(elegidas) <= permitidas
    # Al muestrear sigue habiendo variedad entre las dos seguras.
    assert len(elegidas) == 2


def test_nivel_bajo_si_todas_las_candidatas_permiten_mate_cae_en_la_mejor_de_la_red(monkeypatch):
    """Mismo fallback que el modo maestro: no se inventa una jugada fuera del pool."""
    tablero = chess.Board(FEN_MATE_DEL_RIVAL)
    # Las 7 jugadas que permiten mate en 1 (torre por la columna a, o Tb1) ocupan el pool.
    _usar_modelo_falso(
        monkeypatch,
        tablero,
        {
            "a1a7": 9.0, "a1a6": 8.5, "a1a5": 8.0, "a1a4": 7.5,
            "a1a3": 7.0, "a1a2": 6.5, "a1b1": 6.0,
        },
    )
    esperado = predecir_jugada_maestra(FEN_MATE_DEL_RIVAL)  # modo maestro, mismo fallback
    assert esperado == "Ra7"
    assert predecir_jugada_maestra(FEN_MATE_DEL_RIVAL, nivel=0, rng=random.Random(3)) == "Ra7"


def test_nivel_bajo_penaliza_la_pieza_colgada_antes_de_muestrear(monkeypatch):
    """La torre colgada (Ra8, penalidad 10) tiene el mejor logit de la red, pero el
    castigo se resta antes del softmax: a nivel bajo se elige poco, no nunca."""
    tablero = chess.Board(FEN_MATE_DEL_RIVAL)
    ra8 = chess.Move.from_uci("a1a8")
    assert inferencia._evaluar_candidata_tactica(tablero, ra8)["penalidad_pieza_colgada"] == 10.0
    _usar_modelo_falso(monkeypatch, tablero, {"a1a8": 6.0, "g1f1": 5.0, "g1h1": 4.9})

    assert predecir_jugada_maestra(FEN_MATE_DEL_RIVAL) == "Kf1"  # maestro: nunca la cuelga

    rng = random.Random(11)
    elegidas = Counter(predecir_jugada_maestra(FEN_MATE_DEL_RIVAL, nivel=0, rng=rng) for _ in range(1000))
    assert 0 < elegidas["Ra8"] / 1000 < 0.08  # sin penalidad sería ~41 %
    assert set(elegidas) <= {"Ra8", "Kf1", "Kh1"}


@pytest.mark.parametrize("nivel", NIVELES_BAJOS)
def test_nivel_bajo_con_red_sin_entrenar_devuelve_siempre_jugada_legal(checkpoint_de_prueba, nivel):
    fens = [
        chess.STARTING_FEN,
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4",
        FEN_MATE_DEL_RIVAL,
    ]
    rng = random.Random(0)
    for fen in fens:
        tablero = chess.Board(fen)
        legales = {tablero.san(m) for m in tablero.legal_moves}
        for _ in range(15):
            assert predecir_jugada_maestra(fen, checkpoint_de_prueba, nivel=nivel, rng=rng) in legales


def test_nivel_bajo_sin_rng_usa_uno_propio_y_devuelve_jugada_legal(checkpoint_de_prueba):
    tablero = chess.Board()
    legales = {tablero.san(m) for m in tablero.legal_moves}
    assert predecir_jugada_maestra(tablero.fen(), checkpoint_de_prueba, nivel=3) in legales


def test_nivel_bajo_con_una_sola_jugada_legal_la_devuelve(checkpoint_de_prueba):
    fen = "k7/2K5/8/8/8/8/8/1R6 b - - 0 1"  # negras: única jugada legal, Ka7
    tablero = chess.Board(fen)
    legales = list(tablero.legal_moves)
    assert len(legales) == 1
    assert predecir_jugada_maestra(fen, checkpoint_de_prueba, nivel=0) == tablero.san(legales[0])


def test_nivel_bajo_sin_jugadas_legales_falla(checkpoint_de_prueba):
    fen_ahogado = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    with pytest.raises(ValueError):
        predecir_jugada_maestra(fen_ahogado, checkpoint_de_prueba, nivel=0)
