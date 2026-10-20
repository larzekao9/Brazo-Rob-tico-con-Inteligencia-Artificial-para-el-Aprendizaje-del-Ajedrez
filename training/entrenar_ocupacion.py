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
from training.entrenar_piezas_propio import _augmentar_fuerte
from training.entrenar_valor import elegir_dispositivo
from training.reentrenar_con_dataset_propio import SEMILLA, _cargar_dataset_propio, _separar_train_valid

EPOCAS = 40
TAMANO_LOTE = 16


class _Casillas(Dataset):
    def __init__(self, muestras, augmentar: bool):
        self.muestras, self.augmentar = muestras, augmentar

    def __len__(self) -> int:
        return len(self.muestras)

    def __getitem__(self, i: int):
        recorte, clase = self.muestras[i]
        if self.augmentar:
            recorte = _augmentar_fuerte(recorte)
        return tensor_de_recorte(recorte), CLASES_OCUPACION.index(clase)


def entrenar() -> None:
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)
    torch.manual_seed(SEMILLA)
    dispositivo = elegir_dispositivo()
    muestras = [(imagen, clase_a_ocupacion(clase)) for imagen, clase in _cargar_dataset_propio()]
    cuenta = Counter(c for _, c in muestras)
    print(f"{len(muestras)} fotos: {dict(cuenta)}")
    train, valid = _separar_train_valid(muestras, 0.2)
    pesos = torch.tensor([1.0 / max(1, Counter(c for _, c in train)[k]) for k in CLASES_OCUPACION])
    pesos = (pesos / pesos.mean()).to(dispositivo)
    modelo = RedClasificadoraPiezas(cantidad_clases=len(CLASES_OCUPACION)).to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=1e-3, weight_decay=1e-4)
    perdida_fn = nn.CrossEntropyLoss(weight=pesos)
    cargador = DataLoader(_Casillas(train, True), batch_size=TAMANO_LOTE, shuffle=True)
    cargador_valid = DataLoader(_Casillas(valid, False), batch_size=TAMANO_LOTE)

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
    torch.save({"pesos": {k: v.cpu() for k, v in modelo.state_dict().items()}, "clases": CLASES_OCUPACION}, RUTA_CHECKPOINT)
    print(f"Guardado en {RUTA_CHECKPOINT}")


if __name__ == "__main__":
    entrenar()
