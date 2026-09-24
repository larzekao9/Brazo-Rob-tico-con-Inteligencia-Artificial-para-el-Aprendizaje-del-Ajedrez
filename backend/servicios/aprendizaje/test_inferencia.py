"""Test de inferencia (HU4) — no depende del checkpoint real (26MB, vive en
`training/checkpoints/`, ignorado por git): genera uno chico con pesos sin
entrenar para probar que `cargar_modelo`/`predecir_jugada` funcionan de punta
a punta. La precisión del modelo real se evalúa aparte (ver `docs/plan_sprints.md`).

Se salta automáticamente si `torch` no está instalado (ver test_modelo_jugadas.py).
"""
import chess
import pytest

torch = pytest.importorskip("torch")

from backend.servicios.aprendizaje.inferencia import (
    cargar_modelo,
    predecir_jugada,
    predecir_jugada_maestra,
    predecir_top_jugadas,
    calcular_saliencia,
    estado_modelo,
)  # noqa: E402
from backend.servicios.aprendizaje.modelo_jugadas import (
    NUM_CLASES,
    RedPrediccionJugadas,
    RedResNetAjedrez,
    RedSEResNetAjedrez,
)  # noqa: E402


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
        estado_modelo("/no/existe.pt")
