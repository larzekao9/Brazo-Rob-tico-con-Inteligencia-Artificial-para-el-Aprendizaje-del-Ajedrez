import cv2
import numpy as np
import pytest

import training.capturar_dataset_propio as capturar_dataset_propio
from training.capturar_dataset_propio import capturar_muestras, fen_piezas_a_ocupacion

# Mismo enfoque que backend/servicios/vision/test_tablero.py: un cuadrilátero
# de color uniforme alcanza para que detectar_esquinas_tablero lo encuentre,
# sin depender de una foto real.
_ESQUINAS_TABLERO_SINTETICO = np.array(
    [[150, 80], [750, 40], [780, 620], [120, 660]], dtype=np.int32
)


def _crear_foto_de_prueba(tmp_path):
    imagen = np.full((700, 900, 3), 200, dtype=np.uint8)
    cv2.fillConvexPoly(imagen, _ESQUINAS_TABLERO_SINTETICO, (60, 60, 60))
    ruta = tmp_path / "foto_prueba.jpg"
    cv2.imwrite(str(ruta), imagen)
    return ruta


def test_posicion_inicial_estandar() -> None:
    ocupacion = fen_piezas_a_ocupacion("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
    assert ocupacion["a1"] == "white-rook"
    assert ocupacion["e1"] == "white-king"
    assert ocupacion["d8"] == "black-queen"
    assert ocupacion["e8"] == "black-king"
    assert ocupacion["a2"] == "white-pawn"
    assert ocupacion["h7"] == "black-pawn"
    assert "e4" not in ocupacion  # casilla vacía en la posición inicial
    assert len(ocupacion) == 32


def test_posicion_ilegal_con_varias_damas_es_valida_para_etiquetar() -> None:
    # A propósito: no hace falta que sea una partida legal, solo decir qué
    # pieza hay en cada casilla que se ocupó.
    ocupacion = fen_piezas_a_ocupacion("QQQQQQQQ/8/8/8/8/8/8/qqqqqqqq")
    assert ocupacion["a8"] == "white-queen"
    assert ocupacion["h8"] == "white-queen"
    assert ocupacion["a1"] == "black-queen"
    assert len(ocupacion) == 16


def test_tablero_vacio() -> None:
    assert fen_piezas_a_ocupacion("8/8/8/8/8/8/8/8") == {}


def test_menos_de_8_filas_lanza_valueerror() -> None:
    with pytest.raises(ValueError):
        fen_piezas_a_ocupacion("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP")


def test_fila_que_no_suma_8_columnas_lanza_valueerror() -> None:
    with pytest.raises(ValueError):
        fen_piezas_a_ocupacion("rnbqkbn/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")  # falta una pieza en la primera fila


def test_caracter_invalido_lanza_valueerror() -> None:
    with pytest.raises(ValueError):
        fen_piezas_a_ocupacion("xnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")


def test_capturar_muestras_con_archivo_guarda_64_casillas_y_control(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(capturar_dataset_propio, "CARPETA_DATASET", tmp_path)
    ruta_foto = _crear_foto_de_prueba(tmp_path)

    cantidad = capturar_muestras("8/8/8/8/8/8/8/8", str(ruta_foto))

    assert cantidad == 64
    assert (tmp_path / "vacia").is_dir()
    assert len(list((tmp_path / "vacia").glob("*.png"))) == 64
    assert (tmp_path / "_ultima_captura.jpg").exists()


def test_capturar_muestras_con_archivo_inexistente_lanza_valueerror(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(capturar_dataset_propio, "CARPETA_DATASET", tmp_path)
    with pytest.raises(ValueError):
        capturar_muestras("8/8/8/8/8/8/8/8", str(tmp_path / "no-existe.jpg"))


def test_con_esquinas_calibradas_guarda_el_cuadro_completo_y_se_borra_con_la_captura(tmp_path, monkeypatch) -> None:
    import cv2
    import numpy as np

    import training.capturar_dataset_propio as capturar
    from backend.servicios.vision import dataset_propio
    from training.entrenar_piezas_propio import _cargar_ampliados

    dataset = tmp_path / "dataset_propio"
    monkeypatch.setattr(capturar, "CARPETA_DATASET", dataset)
    esquinas = np.array([[150, 100], [750, 100], [750, 650], [150, 650]], dtype=np.float32)
    monkeypatch.setattr(capturar, "esquinas_y_margen", lambda imagen, *a, **k: (esquinas, 0.0))
    monkeypatch.setattr("training.entrenar_piezas_propio.CARPETA_DATASET_PROPIO", dataset)
    imagen = np.full((700, 900, 3), 120, dtype=np.uint8)

    captura_id, guardadas = capturar.capturar_muestras_con_id("4k3/8/8/8/8/8/8/4K3", imagen=imagen)

    assert guardadas == 64
    assert (tmp_path / "dataset_propio_cuadros" / f"{captura_id}.jpg").is_file()
    muestras = _cargar_ampliados()
    assert len(muestras) == 64 and {c for _, c, _ in muestras} == {"black-king", "white-king", "vacia"}
    assert muestras[0][0].shape == (96, 96, 3)
    monkeypatch.setattr(dataset_propio, "_carpeta", lambda: dataset)
    assert dataset_propio.borrar_captura(captura_id) == 64
    assert not (tmp_path / "dataset_propio_cuadros" / f"{captura_id}.json").exists()


def test_puntuar_cuenta_ocupacion_y_tipo_de_pieza_solo_en_casillas_con_pieza() -> None:
    from backend.servicios.vision.jugada_probable import NOMBRES
    from backend.servicios.vision.modelo_piezas import CLASES
    from training.evaluar_reconocimiento import puntuar

    verdad = {n: "vacia" for n in NOMBRES}
    verdad["a1"], verdad["e8"] = "white-rook", "black-king"
    probs_o = np.zeros((64, 3))
    probs_p = np.zeros((64, len(CLASES)))
    for i, nombre in enumerate(NOMBRES):
        clase = verdad[nombre]
        probs_o[i, ["vacia", "blanca", "negra"].index("vacia" if clase == "vacia" else "blanca" if clase.startswith("white") else "negra")] = 1
        probs_p[i, CLASES.index(clase)] = 1
    probs_p[NOMBRES.index("e8")] = 0
    probs_p[NOMBRES.index("e8"), CLASES.index("black-queen")] = 1  # el rey negro se lee como dama

    assert puntuar(verdad, probs_o, probs_p, list(CLASES)) == {"ocupacion_ok": 64, "ocupacion_total": 64, "pieza_ok": 1, "pieza_total": 2, "exacta": 1}
    assert puntuar(verdad, probs_o, None, None)["pieza_total"] == 0


def _preparar_captura_calibrada(tmp_path, monkeypatch):
    """Dataset en `tmp_path` con las esquinas calibradas del tablero sintético de `test_validacion_orientacion`."""
    import training.capturar_dataset_propio as capturar
    from backend.servicios.vision.test_validacion_orientacion import ESQUINAS

    dataset = tmp_path / "dataset_propio"
    monkeypatch.setattr(capturar, "CARPETA_DATASET", dataset)
    monkeypatch.setattr(capturar, "esquinas_y_margen", lambda imagen, *a, **k: (ESQUINAS, 0.0))
    return capturar, dataset


def test_captura_con_la_calibracion_girada_se_rechaza_sin_guardar_nada(tmp_path, monkeypatch) -> None:
    from backend.servicios.vision.test_validacion_orientacion import INICIAL, foto_con_piezas
    from backend.servicios.vision.validacion_orientacion import girar_casilla

    capturar, dataset = _preparar_captura_calibrada(tmp_path, monkeypatch)
    foto_girada = foto_con_piezas({girar_casilla(c): e for c, e in INICIAL.items()})  # las blancas se ven arriba (filas 7-8)

    with pytest.raises(ValueError, match="180"):
        capturar.capturar_muestras_con_id("rrrrrrrr/pppppppp/8/8/8/8/PPPPPPPP/RRRRRRRR", imagen=foto_girada)
    assert not list(dataset.glob("*/*.png")) and not (tmp_path / "dataset_propio_cuadros").exists()

    _, guardadas = capturar.capturar_muestras_con_id("rrrrrrrr/pppppppp/8/8/8/8/PPPPPPPP/RRRRRRRR", imagen=foto_con_piezas(INICIAL))
    assert guardadas == 64


def test_corregir_capturas_invertidas_gira_las_esquinas_y_vuelve_a_recortar(tmp_path, monkeypatch) -> None:
    import json

    from backend.servicios.vision import validacion_orientacion
    from backend.servicios.vision.test_validacion_orientacion import ESQUINAS, INICIAL, foto_con_piezas

    capturar, dataset = _preparar_captura_calibrada(tmp_path, monkeypatch)
    foto_girada = foto_con_piezas({validacion_orientacion.girar_casilla(c): e for c, e in INICIAL.items()})
    captura_id, _ = capturar.capturar_muestras_con_id(
        "rrrrrrrr/pppppppp/8/8/8/8/PPPPPPPP/RRRRRRRR", imagen=foto_girada, validar_orientacion=False
    )
    antes = {p.relative_to(dataset) for p in dataset.glob("*/*.png")}

    assert [e["captura"] for e in capturar.corregir_capturas_invertidas()] == [captura_id]  # sin aplicar solo lista
    assert capturar.corregir_capturas_invertidas(aplicar=True)[0]["corregida"]

    manifiesto = json.loads((tmp_path / "dataset_propio_cuadros" / f"{captura_id}.json").read_text())
    assert np.array_equal(np.array(manifiesto["esquinas"], dtype=np.float32), validacion_orientacion.girar_esquinas(ESQUINAS))
    assert {p.relative_to(dataset) for p in dataset.glob("*/*.png")} == antes  # mismas clases y casillas, recortes nuevos
    recorte_a1 = cv2.imread(str(dataset / "white-rook" / f"{captura_id}_a1.png"))
    assert recorte_a1.mean() > 120  # ahora la "torre blanca" de a1 es el disco claro
    assert capturar.corregir_capturas_invertidas() == []


def test_captura_de_una_pieza_guarda_las_demas_como_vacias_seguras(tmp_path, monkeypatch) -> None:
    import json

    from backend.servicios.vision.test_validacion_orientacion import foto_con_piezas

    capturar, dataset = _preparar_captura_calibrada(tmp_path, monkeypatch)
    captura_id, guardadas = capturar.capturar_muestras_con_id(
        "8/8/8/8/4P3/8/8/8", imagen=foto_con_piezas({"e4": "white-pawn"}), solo_piezas=True
    )
    manifiesto = json.loads((tmp_path / "dataset_propio_cuadros" / f"{captura_id}.json").read_text())
    assert guardadas == 1 and manifiesto["etiquetas"] == {"e4": "white-pawn"}
    assert len(manifiesto["vacias_seguras"]) == 63 and "e4" not in manifiesto["vacias_seguras"]
    assert not (dataset / "vacia").exists()  # las vacías no van al dataset de piezas


def test_captura_completa_no_agrega_vacias_seguras(tmp_path, monkeypatch) -> None:
    import json

    capturar, _ = _preparar_captura_calibrada(tmp_path, monkeypatch)
    captura_id, _ = capturar.capturar_muestras_con_id("8/8/8/8/8/8/8/8", imagen=np.full((750, 900, 3), 110, np.uint8))
    assert "vacias_seguras" not in json.loads((tmp_path / "dataset_propio_cuadros" / f"{captura_id}.json").read_text())
