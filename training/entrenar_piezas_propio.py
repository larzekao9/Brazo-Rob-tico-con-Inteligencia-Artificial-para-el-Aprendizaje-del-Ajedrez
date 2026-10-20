"""Entrena el clasificador de piezas desde cero SOLO con las fotos propias (`training/dataset_propio/`).

Sirve cuando no hay checkpoint base ni dataset de Roboflow (caso de esta instalación): arma el checkpoint que lee
`backend/servicios/vision/piezas.py` con la misma red y el mismo preprocesamiento. Valida con un 20 % apartado por clase y guarda
la mejor época. Con pocas fotos por clase el resultado es modesto: conviene sumar fotos (variando casilla, luz y ángulo) y repetir,
o entrenar el ZIP del dataset en Colab (`training/colab_vision_piezas.ipynb`).

Uso:
    python -m training.entrenar_piezas_propio
"""
from __future__ import annotations

import random
import shutil
from collections import Counter

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from backend.servicios.vision.modelo_piezas import CLASES, RedClasificadoraPiezas, preprocesar_recorte
from training.entrenar_clasificador_piezas import _augmentar
from training.reentrenar_con_dataset_propio import (
    CARPETA_DATASET_PROPIO,
    RUTA_CHECKPOINT,
    SEMILLA,
    _cargar_dataset_propio,
    _pesos_por_clase,
    _separar_train_valid,
)
from training.entrenar_valor import elegir_dispositivo

EPOCAS = 80
TASA_APRENDIZAJE = 1e-3
TAMANO_LOTE = 16


def _augmentar_fuerte(recorte: np.ndarray) -> np.ndarray:
    """Rotación/brillo de `_augmentar` + espejo horizontal, desplazamiento y zoom leves y algo de desenfoque/ruido."""
    recorte = _augmentar(recorte)
    if random.random() < 0.5:
        recorte = cv2.flip(recorte, 1)
    alto, ancho = recorte.shape[:2]
    escala = random.uniform(0.9, 1.15)
    matriz = np.float32([[escala, 0, random.uniform(-0.08, 0.08) * ancho], [0, escala, random.uniform(-0.08, 0.08) * alto]])
    recorte = cv2.warpAffine(recorte, matriz, (ancho, alto), borderMode=cv2.BORDER_REFLECT)
    if random.random() < 0.3:
        recorte = cv2.GaussianBlur(recorte, (3, 3), 0)
    if random.random() < 0.3:
        recorte = np.clip(recorte.astype(np.float32) + np.random.normal(0, 6, recorte.shape), 0, 255).astype(np.uint8)
    return recorte


class _Casillas(Dataset):
    def __init__(self, muestras: list[tuple[np.ndarray, str]], augmentar: bool):
        self.muestras, self.augmentar = muestras, augmentar

    def __len__(self) -> int:
        return len(self.muestras)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        recorte, clase = self.muestras[i]
        if self.augmentar:
            recorte = _augmentar_fuerte(recorte)
        return preprocesar_recorte(recorte), CLASES.index(clase)


def _evaluar(modelo: nn.Module, cargador: DataLoader, dispositivo) -> tuple[float, list[tuple[int, int]]]:
    modelo.eval()
    pares: list[tuple[int, int]] = []
    with torch.no_grad():
        for entradas, etiquetas in cargador:
            prediccion = modelo(entradas.to(dispositivo)).argmax(dim=1).cpu()
            pares += list(zip(etiquetas.tolist(), prediccion.tolist()))
    return (sum(a == b for a, b in pares) / len(pares) if pares else 0.0), pares


def entrenar() -> None:
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)
    torch.manual_seed(SEMILLA)
    dispositivo = elegir_dispositivo()
    muestras = _cargar_dataset_propio()
    if not muestras:
        raise FileNotFoundError(f"No hay fotos en {CARPETA_DATASET_PROPIO}/")
    print(f"Dispositivo: {dispositivo} — {len(muestras)} fotos: {dict(sorted(Counter(c for _, c in muestras).items()))}")
    train, valid = _separar_train_valid(muestras, 0.2)
    print(f"Entrenamiento: {len(train)} — validación (apartada): {len(valid)}")

    cargador_train = DataLoader(_Casillas(train, True), batch_size=TAMANO_LOTE, shuffle=True)
    cargador_valid = DataLoader(_Casillas(valid, False), batch_size=TAMANO_LOTE)
    modelo = RedClasificadoraPiezas(cantidad_clases=len(CLASES)).to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=TASA_APRENDIZAJE, weight_decay=1e-4)
    perdida_fn = nn.CrossEntropyLoss(weight=_pesos_por_clase(train).to(dispositivo))

    mejor, mejores_pesos = -1.0, None
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
        if exactitud >= mejor:
            mejor = exactitud
            mejores_pesos = {k: v.detach().cpu().clone() for k, v in modelo.state_dict().items()}
        if epoca % 5 == 0 or epoca == 1:
            print(f"Época {epoca:3d}/{EPOCAS} — pérdida {total / len(train):.4f} — validación {exactitud:.3f}")

    modelo.load_state_dict(mejores_pesos)
    exactitud, pares = _evaluar(modelo, cargador_valid, dispositivo)
    print(f"Mejor validación: {exactitud:.3f}")
    errores = Counter((CLASES[a], CLASES[b]) for a, b in pares if a != b)
    for (real, predicha), n in errores.most_common(10):
        print(f"  confundió {real} con {predicha}: {n}")
    RUTA_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    if RUTA_CHECKPOINT.exists():
        shutil.copy(RUTA_CHECKPOINT, RUTA_CHECKPOINT.with_suffix(".anterior.pt"))
    torch.save({"pesos": {k: v.cpu() for k, v in modelo.state_dict().items()}, "clases": CLASES}, RUTA_CHECKPOINT)
    print(f"Checkpoint guardado en {RUTA_CHECKPOINT}")


if __name__ == "__main__":
    entrenar()
