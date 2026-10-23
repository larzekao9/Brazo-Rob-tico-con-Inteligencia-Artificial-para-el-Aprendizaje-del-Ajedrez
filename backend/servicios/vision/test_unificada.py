"""Verificación de la calibración unificada con un tablero sintético visto desde dos cámaras."""
import cv2
import numpy as np
import pytest

from backend.servicios.vision import unificada

LADO = 1000


def _tablero_sintetico() -> np.ndarray:
    """Tablero 8x8 con marco, letras y manchas que no tienen simetría (para que cada giro se distinga)."""
    imagen = np.full((LADO, LADO, 3), 200, dtype=np.uint8)
    for fila in range(8):
        for columna in range(8):
            color = (40, 40, 40) if (fila + columna) % 2 == 0 else (190, 190, 190)
            cv2.rectangle(imagen, (100 + columna * 100, 100 + fila * 100), (200 + columna * 100, 200 + fila * 100), color, -1)
    azar = np.random.default_rng(3)
    for _ in range(25):  # manchas de madera: textura asimétrica
        cv2.circle(imagen, tuple(int(v) for v in azar.integers(10, LADO - 10, 2)), int(azar.integers(4, 14)), tuple(int(v) for v in azar.integers(60, 230, 3)), -1)
    cv2.putText(imagen, "A B C D E F G H", (130, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 4)
    cv2.putText(imagen, "8 7 6 5", (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 3)
    return imagen


def _camara(tablero: np.ndarray, giro: int, perspectiva: float):
    """Foto de `tablero` (rotado `giro` grados como si la cámara mirara desde otro lado) y las 4 esquinas del área de juego, en el orden a8, h8, h1, a1."""
    esquinas = np.array([[100, 100], [900, 100], [900, 900], [100, 900]], dtype=np.float32)  # a8, h8, h1, a1 en el tablero sintético
    destino = np.array([[120, 90], [880 - perspectiva, 130], [850 - perspectiva, 850], [150, 880]], dtype=np.float32) + 60
    matriz = cv2.getPerspectiveTransform(esquinas, destino)
    foto = cv2.warpPerspective(tablero, matriz, (1100, 1100), borderValue=(120, 120, 120))
    puntos = cv2.perspectiveTransform(esquinas.reshape(-1, 1, 2), matriz).reshape(4, 2)
    return foto, puntos


def _girar_foto_y_esquinas(foto, puntos, giro):
    """Gira la foto (cámara montada girada) y lleva las esquinas con ella: lo que vería esa cámara, calibrada correctamente."""
    if giro == 0:
        return foto, puntos
    codigo = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}[giro]
    alto, ancho = foto.shape[:2]
    girada = cv2.rotate(foto, codigo)
    if giro == 90:
        nuevos = np.array([[alto - y, x] for x, y in puntos])
    elif giro == 180:
        nuevos = np.array([[ancho - x, alto - y] for x, y in puntos])
    else:
        nuevos = np.array([[y, ancho - x] for x, y in puntos])
    return girada, nuevos.astype(np.float32)


def test_dos_camaras_bien_calibradas_coinciden() -> None:
    tablero = _tablero_sintetico()
    foto_1, esq_1 = _camara(tablero, 0, 0)
    foto_2, esq_2 = _camara(tablero, 0, 40)
    foto_2, esq_2 = _girar_foto_y_esquinas(foto_2, esq_2, 180)  # la segunda cámara está montada del revés, pero bien calibrada
    informe = unificada.comparar(foto_1, foto_2, esq_1, esq_2)
    assert informe["nivel"] == "bien" and informe["ok"] and informe["error_casillas"] < 0.15
    assert informe["orientacion"]["mejor"] == "sin giro" and informe["imagen"]


def test_detecta_la_secundaria_calibrada_con_las_esquinas_en_otro_orden() -> None:
    tablero = _tablero_sintetico()
    foto_1, esq_1 = _camara(tablero, 0, 0)
    foto_2, esq_2 = _camara(tablero, 0, 40)
    esq_mal = np.roll(esq_2, 2, axis=0)  # el usuario marcó a1 donde iba h8: el tablero queda girado 180°
    informe = unificada.comparar(foto_1, foto_2, esq_1, esq_mal)
    assert informe["nivel"] == "orientacion" and not informe["ok"] and "180" in informe["orientacion"]["mejor"]


def test_detecta_un_corrimiento_grande() -> None:
    tablero = _tablero_sintetico()
    foto_1, esq_1 = _camara(tablero, 0, 0)
    foto_2, esq_2 = _camara(tablero, 0, 0)
    informe = unificada.comparar(foto_1, foto_2, esq_1, esq_2 + np.float32([60, 0]))  # esquinas corridas ~60 px de la foto
    assert informe["nivel"] in ("regular", "mal") and informe["error_casillas"] > 0.15


def test_verificar_sin_calibrar_lanza_valueerror(tmp_path, monkeypatch) -> None:
    from backend.servicios.vision import tablero

    monkeypatch.setattr(tablero, "ARCHIVO_ESQUINAS", tmp_path / "esquinas.json")
    imagen = np.zeros((100, 100, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        unificada.verificar(imagen, imagen)


def test_una_esquina_mal_marcada_se_ve_por_esquina_aunque_el_corrimiento_global_sea_chico() -> None:
    tablero = _tablero_sintetico()
    foto_1, esq_1 = _camara(tablero, 0, 0)
    foto_2, esq_2 = _camara(tablero, 0, 40)
    mal = esq_2.copy()
    mal[1] += np.float32([35, -28])  # h8 marcada ~45 px corrida: el resto del tablero sigue casi en su lugar
    informe = unificada.comparar(foto_1, foto_2, esq_1, mal)
    assert informe["por_esquina"] is not None and informe["por_esquina"]["esquinas_medidas"] >= unificada.MINIMO_ESQUINAS
    assert informe["error_casillas"] > informe["corrimiento_global"]["error_casillas"]
    assert informe["nivel"] in ("regular", "mal") and "secundaria" in informe["mensaje"]
    secundaria = informe["camaras"]["secundaria"]
    assert secundaria["sugeridas"]["error_casillas"] < secundaria["error_max_casillas"]


def test_sugerir_esquinas_recupera_las_esquinas_verdaderas() -> None:
    foto, verdaderas = _camara(_tablero_sintetico(), 0, 40)
    marcadas = verdaderas + np.float32([[6, -4], [-5, 7], [4, 5], [-7, -3]])  # clics imprecisos de unos pocos píxeles
    sugerencia = unificada.sugerir_esquinas(foto, marcadas)
    assert sugerencia is not None and sugerencia["esquinas_medidas"] >= 45
    assert np.abs(sugerencia["esquinas_enderezado"] - verdaderas).max() < 1.5
    assert sugerencia["error_sugeridas_casillas"] < sugerencia["error_actual_casillas"]
    assert list(sugerencia["esquinas"]) == ["a8", "h8", "h1", "a1"]


def test_con_piezas_tapando_las_esquinas_no_se_sugiere_nada() -> None:
    foto, esquinas = _camara(_tablero_sintetico(), 0, 0)
    tapada = enderezada = foto.copy()
    for x in range(160, 1100, 45):
        for y in range(150, 1100, 45):
            cv2.circle(tapada, (x, y), 20, (230, 230, 230), -1)  # "piezas" por todo el tablero
    assert unificada.sugerir_esquinas(enderezada, esquinas) is None
    informe = unificada.comparar(foto, tapada, esquinas, esquinas)
    assert informe["por_esquina"] is None and "piezas" in informe["mensaje"]


def test_detecta_la_secundaria_espejada_y_girada_90() -> None:
    tablero = _tablero_sintetico()
    foto_1, esq_1 = _camara(tablero, 0, 0)
    foto_2, esq_2 = _camara(tablero, 0, 40)
    espejada = unificada.comparar(foto_1, foto_2, esq_1, esq_2[[1, 0, 3, 2]])  # a8 <-> h8 y h1 <-> a1
    girada = unificada.comparar(foto_1, foto_2, esq_1, np.roll(esq_2, 1, axis=0))
    assert espejada["nivel"] == "orientacion" and espejada["orientacion"]["mejor"] == "espejada"
    assert girada["nivel"] == "orientacion" and girada["orientacion"]["mejor"] in ("girada 90°", "girada 270°")


def test_luz_y_contraste_distintos_no_parecen_un_giro() -> None:
    """Dos cámaras bien calibradas con exposición, color y ruido muy distintos: antes, con solo los bordes, salía "espejada"."""
    tablero = _tablero_sintetico()
    foto_1, esq_1 = _camara(tablero, 0, 0)
    foto_2, esq_2 = _camara(tablero, 0, 40)
    ruido = np.random.default_rng(5).normal(0, 18, foto_2.shape)
    foto_2 = np.clip(foto_2.astype(np.float32) * np.float32([0.6, 0.9, 1.3]) + 25 + ruido, 0, 255).astype(np.uint8)
    informe = unificada.comparar(foto_1, foto_2, esq_1, esq_2)
    assert informe["nivel"] != "orientacion" and informe["orientacion"]["mejor"] == "sin giro"
