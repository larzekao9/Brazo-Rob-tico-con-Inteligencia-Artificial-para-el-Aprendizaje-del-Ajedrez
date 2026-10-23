"""Entrena el clasificador de ocupación (vacía / blanca / negra) con `training/dataset_propio/`.

Reusa las fotos de las 13 clases juntándolas en 3 (todas las piezas blancas -> "blanca", etc.). Usa el centro de la casilla y la
misma aumentación fuerte que el clasificador de piezas. Guarda `training/checkpoints/clasificador_ocupacion.pt`.

Uso:
    python -m training.entrenar_ocupacion
"""
from __future__ import annotations

import random
from collections import Counter

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from backend.servicios.vision.modelo_piezas import RedClasificadoraPiezas
from backend.servicios.vision.ocupacion import CLASES_OCUPACION, RUTA_CHECKPOINT, clase_a_ocupacion, tensor_de_recorte
from training.entrenar_piezas_propio import _augmentar_fuerte, separar_por_captura
from training.entrenar_valor import elegir_dispositivo
from training.reentrenar_con_dataset_propio import CARPETA_DATASET_PROPIO, SEMILLA, _cargar_dataset_propio_por_foto

EPOCAS = 40
TAMANO_LOTE = 16


MINIMO_BASE = 100
"""Casillas con cuadro completo que hacen falta para entrenar con el recorte de la base."""
DISTANCIA_VACIAS_SEGURAS = 2
"""De las `vacias_seguras` de una captura de pocas piezas se usan las que están a esta distancia (en casillas, contando diagonales) o menos
de alguna pieza: es donde cae la cabeza de una pieza inclinada, el caso que el modelo confundía con "ocupada". Las lejanas son casillas
vacías comunes, que ya sobran, y solo desbalancearían las clases."""


def _distancia(a: str, b: str) -> int:
    return max(abs(ord(a[0]) - ord(b[0])), abs(int(a[1]) - int(b[1])))


def vacias_cercanas(datos: dict) -> list[str]:
    """Las `vacias_seguras` del manifiesto `datos` a `DISTANCIA_VACIAS_SEGURAS` o menos de alguna pieza de sus `etiquetas`."""
    piezas = [c for c, clase in datos["etiquetas"].items() if clase != "vacia"]
    return [c for c in datos.get("vacias_seguras", []) if any(_distancia(c, p) <= DISTANCIA_VACIAS_SEGURAS for p in piezas)]


def _cargar_base() -> list[tuple[np.ndarray, str, str]]:
    """`(recorte de la huella, ocupación, captura)` de cada casilla guardada con su cuadro completo (ver `geometria3d.recortes_base`).

    Además de las casillas etiquetadas, suma como "vacia" las `vacias_seguras` cercanas a una pieza (`vacias_cercanas`), siempre que la captura
    siga en el dataset (que tenga alguno de sus recortes: si se deshizo, no se usa)."""
    import json

    import cv2

    from backend.servicios.vision import geometria3d
    from training.capturar_dataset_propio import carpeta_cuadros

    muestras = []
    for manifiesto in sorted(carpeta_cuadros().glob("*.json")):
        cuadro = cv2.imread(str(manifiesto.with_suffix(".jpg")))
        if cuadro is None:
            continue
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        alto, ancho = cuadro.shape[:2]
        try:
            recortes = geometria3d.recortes_base(
                cuadro, np.array(datos["esquinas"], dtype=np.float32)[::-1], geometria3d.cargar_lente(datos.get("camara", "principal"), ancho, alto)
            )
        except ValueError:
            continue
        vigente = False
        for casilla, clase in datos["etiquetas"].items():
            if (CARPETA_DATASET_PROPIO / clase / f"{manifiesto.stem}_{casilla}.png").exists():
                muestras.append((recortes[casilla], clase_a_ocupacion(clase), manifiesto.stem))
                vigente = True
        if vigente:
            muestras += [(recortes[casilla], "vacia", manifiesto.stem) for casilla in vacias_cercanas(datos)]
    return muestras


class _Casillas(Dataset):
    def __init__(self, muestras, augmentar: bool, modo: str = "centro"):
        self.muestras, self.augmentar, self.modo = muestras, augmentar, modo

    def __len__(self) -> int:
        return len(self.muestras)

    def __getitem__(self, i: int):
        recorte, clase = self.muestras[i]
        if self.augmentar:
            recorte = _augmentar_fuerte(recorte)
        return tensor_de_recorte(recorte, self.modo), CLASES_OCUPACION.index(clase)


def entrenar(recorte: str = "centro") -> None:
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)
    torch.manual_seed(SEMILLA)
    dispositivo = elegir_dispositivo()
    modo = "centro"
    con_marca = []
    if recorte == "base":
        con_marca = _cargar_base()
        if len(con_marca) >= MINIMO_BASE:
            modo = "base"
        else:
            print(f"Solo {len(con_marca)} casillas con cuadro completo (hacen falta {MINIMO_BASE}): se entrena con el recorte del centro.")
    if modo == "centro":
        con_marca = [(i, clase_a_ocupacion(c), m) for i, c, m in _cargar_dataset_propio_por_foto()]
    muestras = [(i, c) for i, c, _ in con_marca]
    cuenta = Counter(c for _, c in muestras)
    print(f"{len(muestras)} fotos: {dict(cuenta)}")
    train, valid = separar_por_captura(con_marca)
    pesos = torch.tensor([1.0 / max(1, Counter(c for _, c in train)[k]) for k in CLASES_OCUPACION])
    pesos = (pesos / pesos.mean()).to(dispositivo)
    modelo = RedClasificadoraPiezas(cantidad_clases=len(CLASES_OCUPACION)).to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=1e-3, weight_decay=1e-4)
    perdida_fn = nn.CrossEntropyLoss(weight=pesos)
    cargador = DataLoader(_Casillas(train, True, modo), batch_size=TAMANO_LOTE, shuffle=True)
    cargador_valid = DataLoader(_Casillas(valid, False, modo), batch_size=TAMANO_LOTE)

    def evaluar() -> tuple[float, list[tuple[int, int]]]:
        modelo.eval()
        pares = []
        with torch.no_grad():
            for x, y in cargador_valid:
                pares += list(zip(y.tolist(), modelo(x.to(dispositivo)).argmax(1).cpu().tolist()))
        return sum(a == b for a, b in pares) / len(pares), pares

    mejor, mejores = -1.0, None
    for epoca in range(1, EPOCAS + 1):
        modelo.train()
        for x, y in cargador:
            optimizador.zero_grad()
            perdida_fn(modelo(x.to(dispositivo)), y.to(dispositivo)).backward()
            optimizador.step()
        exactitud, _ = evaluar()
        if exactitud >= mejor:
            mejor, mejores = exactitud, {k: v.detach().cpu().clone() for k, v in modelo.state_dict().items()}
        if epoca % 10 == 0:
            print(f"Época {epoca}/{EPOCAS} — validación {exactitud:.3f}")
    modelo.load_state_dict(mejores)
    exactitud, pares = evaluar()
    print(f"Mejor validación: {exactitud:.3f}")
    for (real, pred), n in Counter((CLASES_OCUPACION[a], CLASES_OCUPACION[b]) for a, b in pares if a != b).most_common():
        print(f"  confundió {real} con {pred}: {n}")
    RUTA_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"pesos": {k: v.cpu() for k, v in modelo.state_dict().items()}, "clases": CLASES_OCUPACION, "recorte": modo}, RUTA_CHECKPOINT)
    print(f"Guardado en {RUTA_CHECKPOINT}")


if __name__ == "__main__":
    import argparse

    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--recorte", choices=["centro", "base"], default="centro", help="recorte de cada casilla: el centro del recorte justo, o la huella 3D de la base")
    entrenar(analizador.parse_args().recorte)
