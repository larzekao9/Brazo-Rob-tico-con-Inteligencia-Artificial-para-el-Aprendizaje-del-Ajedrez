"""Entrena un modelo CANDIDATO de piezas con el dataset propio (incluidas las casillas corregidas en el probador) y solo reemplaza al actual si lo supera.

Pensado para el botón «Entrenar con mis correcciones» del probador: usa la GPU del Mac (MPS) si hay (ver `elegir_dispositivo`). Los dos
modelos, el actual (`clasificador_piezas.pt`, del formato que sea: red propia o TorchScript de Colab) y el candidato, se miden sobre las MISMAS
capturas apartadas para validar. Las muestras corregidas siempre entran a entrenamiento (se repiten `REPETICIONES_CORRECCION` veces porque son
pocas) y nunca a validación: lo que se compara es qué tan bien reconocen fotos que ninguno vio. Si el candidato gana, el actual se guarda como
`clasificador_piezas.anterior_<fecha>.pt` y el candidato pasa a ser el modelo; si no, el actual queda intacto. El candidato se guarda siempre en
`clasificador_piezas.candidato.pt`. La última línea de la salida es `RESULTADO: reemplazado ...` o `RESULTADO: conservado ...`.

Los recortes de cada casilla son de dos tipos: `ampliado` (2D: la casilla con un margen fijo alrededor) y `volumen` (3D: la caja que ocupa la pieza vista
con el lente de la cámara). El candidato se entrena con el tipo pedido y, si gana, el modelo guarda ese tipo: el reconocimiento y el probador
(vista plana o cajas 3D) lo siguen solos. El modelo actual se mide con SU PROPIO tipo de recorte, sobre las mismas capturas apartadas.

Se entrena con fotos de la cámara PRINCIPAL y, con `--incluir-secundaria`, también con las de la secundaria tomadas desde arriba (cenitales): como la webcam
principal es menos nítida que aquella cámara, esas fotos se degradan hasta igualar la nitidez medida de la webcam, y siempre van solo a entrenamiento: se
valida únicamente con fotos reales de la principal. El modelo actual NO se reemplaza si hay pocas piezas de la principal para validar. Solo se usan fotos de la cámara PRINCIPAL por defecto. Por defecto, además, solo las tomadas con la cámara en su posición actual (esquinas a menos de 40 px de la calibración vigente:
si se la movió, las fotos de antes muestran el tablero desde otro lugar y confunden al modelo; volver a marcar las esquinas de la misma posición no las descarta); `--todas-las-fotos` incluye también las anteriores.

Uso:
    python -m training.entrenar_candidato [--recorte ampliado|volumen] [--todas-las-fotos] [--incluir-secundaria]
"""
from __future__ import annotations

import random
import shutil
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from backend.servicios.vision import piezas
from backend.servicios.vision.modelo_piezas import CLASES, RedClasificadoraPiezas, preprocesar_recorte
from backend.servicios.vision.tablero import TAMANO_RECORTE_AMPLIADO
from training.capturar_dataset_propio import carpeta_ampliados, carpeta_volumen
from training.entrenar_piezas_propio import MINIMO_AMPLIADOS, _cargar_desde_cuadros, _Casillas, _evaluar, separar_por_captura
from training.entrenar_valor import elegir_dispositivo
from training.reentrenar_con_dataset_propio import RUTA_CHECKPOINT, SEMILLA, _pesos_por_clase

RUTA_CANDIDATO = RUTA_CHECKPOINT.with_name("clasificador_piezas.candidato.pt")
PREFIJO_CORRECCION = "corr"
REPETICIONES_CORRECCION = 5
EPOCAS = 50
TASA_APRENDIZAJE = 1e-3
TAMANO_LOTE = 32
MINIMO_PIEZAS_VALIDACION = 50
"""Casillas CON PIEZA de la principal apartadas para validar que hacen falta para reemplazar al modelo actual: con menos, la comparación es puro azar."""
CENITAL_MINIMO = 0.9
"""Cuánto de frente tiene que verse el tablero (`cenital`) en una foto de la secundaria para usarla: la cámara de arriba de antes ronda 0,95 o más."""


def cargar_correcciones(recorte: str = "ampliado") -> list[tuple[np.ndarray, str]]:
    """`(recorte, clase)` de cada casilla corregida en el probador, del tipo `recorte` (`<dataset>_ampliado` o `<dataset>_volumen`/`<clase>/corr<ms>_<camara>_<casilla>.png`)."""
    raiz = carpeta_volumen() if recorte == "volumen" else carpeta_ampliados()
    muestras = []
    for archivo in sorted(raiz.glob(f"*/{PREFIJO_CORRECCION}*.png")):
        recorte = cv2.imread(str(archivo))
        if recorte is not None and archivo.parent.name in CLASES:
            muestras.append((recorte, archivo.parent.name))
    return muestras


def _punto_actual() -> dict | None:
    if not RUTA_CHECKPOINT.exists():
        return None
    return torch.load(RUTA_CHECKPOINT, map_location="cpu", weights_only=False)


def exactitud_del_modelo_actual(valid: list[tuple[np.ndarray, str]], dispositivo: str = "cpu") -> float | None:
    """Acierto del modelo guardado en `RUTA_CHECKPOINT` (de cualquier formato) sobre `valid`, con su propio tamaño de entrada. `None` si no hay.

    `valid` tiene que ser del tipo de recorte del modelo actual (ver `recorte_del_modelo_actual`).
    """
    punto = _punto_actual()
    if punto is None:
        return None
    tamano = int(punto.get("tamano", 64))
    red = piezas.cargar_red(punto, tamano).to(dispositivo).eval()
    clases = list(punto["clases"])
    aciertos = 0
    with torch.no_grad():
        for desde in range(0, len(valid), 64):
            lote = valid[desde : desde + 64]
            entradas = torch.stack([preprocesar_recorte(r, tamano) for r, _ in lote]).to(dispositivo)
            predichas = red(entradas).argmax(dim=1).cpu().tolist()
            aciertos += sum(clases[p] == clase for p, (_, clase) in zip(predichas, lote))
    return aciertos / len(valid) if valid else None


def recorte_del_modelo_actual() -> str:
    """El tipo de recorte (`ampliado` o `volumen`) con el que se entrenó el modelo actual; `justo` se mide como `ampliado`."""
    punto = _punto_actual()
    return "volumen" if punto is not None and punto.get("recorte") == "volumen" else "ampliado"


def esquinas_actuales(camara: str = "principal"):
    """Las esquinas de la calibración vigente de `camara` (orden de `enderezar_tablero`), o `None` si no está calibrada."""
    from backend.servicios.vision import tablero

    return tablero.cargar_esquinas_calibradas(tablero.archivo_esquinas(camara))


def marca_de_la_calibracion(camara: str = "principal") -> int | None:
    """Cuándo se guardó la calibración vigente de `camara`, en milisegundos desde 1970 (la misma escala que el nombre de cada captura), o `None` si no hay."""
    import json
    from datetime import datetime

    from backend.servicios.vision.calibracion_camara import ruta_metadata

    try:
        fecha = json.loads(ruta_metadata(camara).read_text(encoding="utf-8")).get("fecha")
        return int(datetime.fromisoformat(fecha).timestamp() * 1000) if fecha else None
    except (OSError, ValueError, TypeError):
        return None


def nitidez(recorte: np.ndarray) -> float:
    """Varianza del laplaciano del recorte a 96 px: más alta, más nítido."""
    return float(cv2.Laplacian(cv2.cvtColor(cv2.resize(recorte, (96, 96)), cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def degradar(recorte: np.ndarray, fuerza: float, azar: random.Random) -> np.ndarray:
    """Hace que un recorte nítido se vea como el de una webcam: lo achica y lo vuelve a agrandar (pierde detalle) y le suma un desenfoque suave.

    `fuerza` (0 a 1) gradúa las dos cosas a la vez: 0 deja el recorte casi igual y 1 lo achica a ~65 % con un desenfoque de sigma 1,5. Varía un poco de
    recorte en recorte, para que el modelo no aprenda una sola cantidad de borrosidad.
    """
    alto, ancho = recorte.shape[:2]
    f = min(1.0, max(0.0, fuerza * azar.uniform(0.8, 1.2)))
    factor = 1.0 - 0.35 * f
    if f < 0.02:
        return recorte
    chico = cv2.resize(recorte, (max(8, int(ancho * factor)), max(8, int(alto * factor))), interpolation=cv2.INTER_AREA)
    vuelto = cv2.resize(chico, (ancho, alto), interpolation=cv2.INTER_CUBIC)
    sigma = 1.5 * f
    return cv2.GaussianBlur(vuelto, (0, 0), sigma) if sigma > 0.05 else vuelto


def fuerza_para_igualar(nitidas: list[np.ndarray], objetivo: float) -> float:
    """La fuerza de degradación (0 a 1, ver `degradar`) con la que los recortes de `nitidas` quedan tan poco nítidos como `objetivo` (la mediana de la webcam).

    Busca por tanteo sobre una muestra: más fuerza, menos nitidez. Si ya son menos nítidos que el objetivo, 0 (no se los toca).
    """
    muestra = nitidas[:: max(1, len(nitidas) // 200)]
    mejor_fuerza, mejor_distancia = 0.0, float("inf")
    for fuerza in np.arange(0.0, 0.501, 0.01):  # la nitidez cae muy rápido con poca fuerza: pasos finos
        azar = random.Random(7)
        mediana = float(np.median([nitidez(degradar(r, float(fuerza), azar)) for r in muestra]))
        if abs(mediana - objetivo) < mejor_distancia:
            mejor_fuerza, mejor_distancia = float(fuerza), abs(mediana - objetivo)
    return mejor_fuerza


def exactitud_de_piezas(modelo: nn.Module, validacion: list[tuple[np.ndarray, str]], dispositivo: str) -> float:
    """Acierto solo en las casillas CON pieza de `validacion` (las vacías son la mayoría y inflan el acierto total)."""
    piezas_val = [(i, c) for i, c in validacion if c != "vacia"]
    if not piezas_val:
        return 0.0
    return _evaluar(modelo, DataLoader(_Casillas(piezas_val, False, TAMANO_RECORTE_AMPLIADO), batch_size=TAMANO_LOTE), dispositivo)[0]


def entrenar_candidato(recorte: str = "ampliado", solo_posicion_actual: bool = True, incluir_secundaria: bool = False) -> None:
    if recorte not in ("ampliado", "volumen"):
        raise ValueError("recorte debe ser ampliado (2D) o volumen (3D)")
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)
    torch.manual_seed(SEMILLA)
    dispositivo = elegir_dispositivo()
    print(f"Dispositivo de entrenamiento: {dispositivo} — recorte {recorte} ({'3D, caja de la pieza' if recorte == 'volumen' else '2D, casilla con margen'})")
    desde = esquinas_actuales("principal") if solo_posicion_actual else None
    con_marca = _cargar_desde_cuadros(recorte, camaras={"principal"}, cerca_de=desde)
    if desde is not None:
        print(f"Fotos de la cámara principal tomadas con la cámara en su posición actual (esquinas a menos de 40 px de la calibración): {len(con_marca)} casillas")
    if len(con_marca) < MINIMO_AMPLIADOS:
        total = len(_cargar_desde_cuadros(recorte, camaras={"principal"}))
        raise ValueError(
            f"Hacen falta al menos {MINIMO_AMPLIADOS} casillas con cuadro completo de la cámara principal{' en su posición actual' if desde is not None else ''} "
            f"(hay {len(con_marca)}; en total, de la principal, {total}). Saca fotos con la cámara en su posición actual"
            f"{' o entrena con todas las fotos' if desde is not None and total >= MINIMO_AMPLIADOS else ''}"
        )
    correcciones = cargar_correcciones(recorte)
    train, valid = separar_por_captura(con_marca)
    de_la_secundaria: list[tuple[np.ndarray, str]] = []
    if incluir_secundaria:
        sec = _cargar_desde_cuadros(recorte, camaras={"secundaria"}, min_cenital=CENITAL_MINIMO)
        if sec:
            objetivo = float(np.median([nitidez(i) for i, _, _ in con_marca]))
            nitidas = [i for i, _, _ in sec]
            fuerza = fuerza_para_igualar(nitidas, objetivo)
            azar = random.Random(SEMILLA)
            de_la_secundaria = [(degradar(i, fuerza, azar), c) for i, c, _ in sec]
            print(
                f"Secundaria cenital: {len(sec)} casillas (solo entrenamiento). Nitidez {np.median([nitidez(i) for i in nitidas]):.0f} → webcam {objetivo:.0f}: "
                f"se degradan con fuerza {fuerza:.2f} (quedan en {np.median([nitidez(i) for i, _ in de_la_secundaria]):.0f})"
            )
        else:
            print("No hay fotos de la secundaria tomadas desde arriba para sumar.")
    train = train + de_la_secundaria + correcciones * REPETICIONES_CORRECCION
    piezas_valid = sum(c != "vacia" for _, c in valid)
    print(
        f"Entrenamiento: {len(train)} (de ellas {len(de_la_secundaria)} de la secundaria degradada y {len(correcciones)} corregidas x{REPETICIONES_CORRECCION}) "
        f"— validación apartada de la principal: {len(valid)} casillas ({piezas_valid} con pieza)"
    )
    por_clase = dict(sorted(Counter(c for _, c in train).items()))
    print(f"Muestras por clase: {por_clase}")

    cargador_train = DataLoader(_Casillas(train, True, TAMANO_RECORTE_AMPLIADO), batch_size=TAMANO_LOTE, shuffle=True)
    cargador_valid = DataLoader(_Casillas(valid, False, TAMANO_RECORTE_AMPLIADO), batch_size=TAMANO_LOTE)
    modelo = RedClasificadoraPiezas(cantidad_clases=len(CLASES), tamano=TAMANO_RECORTE_AMPLIADO).to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=TASA_APRENDIZAJE, weight_decay=1e-4)
    perdida_fn = nn.CrossEntropyLoss(weight=_pesos_por_clase(train).to(dispositivo))

    mejor, mejores_pesos, mejor_total, mejor_piezas = -1.0, None, 0.0, 0.0
    inicio = time.monotonic()
    for epoca in range(1, EPOCAS + 1):
        modelo.train()
        total = 0.0
        for entradas, etiquetas in cargador_train:
            entradas, etiquetas = entradas.to(dispositivo), etiquetas.to(dispositivo)
            optimizador.zero_grad()
            perdida = perdida_fn(modelo(entradas), etiquetas)
            perdida.backward()
            optimizador.step()
            total += perdida.item() * entradas.size(0)
        exactitud, _ = _evaluar(modelo, cargador_valid, dispositivo)
        en_piezas = exactitud_de_piezas(modelo, valid, dispositivo)
        puntaje = (exactitud + en_piezas) / 2  # el acierto total lo inflan las casillas vacías: se promedia con el de las casillas con pieza
        if puntaje >= mejor:
            mejor, mejor_total, mejor_piezas = puntaje, exactitud, en_piezas
            mejores_pesos = {k: v.detach().cpu().clone() for k, v in modelo.state_dict().items()}
        print(f"Época {epoca}/{EPOCAS} — pérdida {total / len(train):.4f} — validación {exactitud:.3f}, solo piezas {en_piezas:.3f} (mejor {mejor_total:.3f} / {mejor_piezas:.3f}) — {time.monotonic() - inicio:.0f} s", flush=True)

    modelo.load_state_dict(mejores_pesos)
    RUTA_CANDIDATO.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"pesos": mejores_pesos, "clases": CLASES, "tamano": TAMANO_RECORTE_AMPLIADO, "ampliado": True, "recorte": recorte,
         "exactitud_validacion": round(mejor_total, 4), "exactitud_piezas": round(mejor_piezas, 4), "con_secundaria": bool(incluir_secundaria)},
        RUTA_CANDIDATO,
    )
    recorte_actual = recorte_del_modelo_actual()
    if recorte_actual == recorte:
        valid_actual = valid
    else:  # el modelo actual usa el otro tipo de recorte: se lo mide con SUS recortes de las mismas capturas apartadas
        _, valid_actual = separar_por_captura(_cargar_desde_cuadros(recorte_actual, camaras={"principal"}, cerca_de=desde))
    actual = exactitud_del_modelo_actual(valid_actual)
    actual_piezas = exactitud_del_modelo_actual([(i, c) for i, c in valid_actual if c != "vacia"])
    texto_actual = "sin modelo" if actual is None else f"{actual:.3f}, solo piezas {actual_piezas:.3f}"
    print(f"Candidato: {mejor_total:.3f}, solo piezas {mejor_piezas:.3f} — modelo actual: {texto_actual} (mismas fotos de la principal apartadas)")
    if piezas_valid < MINIMO_PIEZAS_VALIDACION:
        print(f"RESULTADO: conservado — hay solo {piezas_valid} casillas con pieza de la principal para validar (hacen falta {MINIMO_PIEZAS_VALIDACION}): "
              f"saca más fotos de piezas con la principal. El candidato queda en {RUTA_CANDIDATO.name}")
        return
    if actual is not None and not (mejor_piezas > actual_piezas and mejor_total >= actual - 0.01):
        print(f"RESULTADO: conservado — el candidato ({mejor_total:.1%}, piezas {mejor_piezas:.1%}) no supera al actual ({actual:.1%}, piezas {actual_piezas:.1%}) en las fotos de la principal; "
              f"queda guardado en {RUTA_CANDIDATO.name}")
        return
    if RUTA_CHECKPOINT.exists():
        shutil.copy(RUTA_CHECKPOINT, RUTA_CHECKPOINT.with_name(f"clasificador_piezas.anterior_{time.strftime('%Y%m%d_%H%M%S')}.pt"))
    shutil.copy(RUTA_CANDIDATO, RUTA_CHECKPOINT)
    RUTA_CHECKPOINT.with_suffix(".json").unlink(missing_ok=True)  # la ficha del modelo de Colab ya no describe al nuevo
    print(f"RESULTADO: reemplazado — el candidato ({mejor_total:.1%}, piezas {mejor_piezas:.1%}) supera al actual ({texto_actual}); el anterior quedó respaldado")


if __name__ == "__main__":
    import argparse

    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--recorte", choices=["ampliado", "volumen"], default="ampliado")
    analizador.add_argument("--todas-las-fotos", action="store_true", help="incluir las fotos de la principal anteriores a su última calibración")
    analizador.add_argument("--incluir-secundaria", action="store_true", help="sumar las fotos de la secundaria tomadas desde arriba, degradadas a la nitidez de la webcam")
    argumentos = analizador.parse_args()
    entrenar_candidato(argumentos.recorte, solo_posicion_actual=not argumentos.todas_las_fotos, incluir_secundaria=argumentos.incluir_secundaria)
