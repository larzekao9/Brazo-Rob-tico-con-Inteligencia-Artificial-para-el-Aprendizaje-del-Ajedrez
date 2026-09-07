"""Entrena la CNN chica que identifica qué pieza hay en una casilla (HU1).

Usa el dataset auto-etiquetado de `dataset_piezas.py` sobre los splits ya
armados en `dataset_tablero/` (train/valid/test, heredados del dataset de
Roboflow). Guarda el mejor checkpoint (por accuracy de validación) en
`training/checkpoints/clasificador_piezas.pt` — ignorado por git, se
referencia por este script, no se commitea (ver CLAUDE.md).

La arquitectura de la red y el preprocesamiento viven en
`backend/servicios/vision/modelo_piezas.py`, no acá — así este script y
`backend/servicios/vision/piezas.py` (que la usa en producción) comparten
exactamente la misma definición sin que uno dependa del otro.

Primera versión: 15 épocas sin compensar el desbalance de clases, 88%/90%
de accuracy en validación/test, pero fallaba sistemáticamente con las damas
(la clase con menos ejemplos) y confundía caballo con torre/alfil. Esta
versión agrega: pesos por clase en la función de pérdida (para que
equivocarse con una dama pese tanto como con un peón), aumentación de datos
(rotación leve + brillo/contraste, solo en entrenamiento) para no depender
tanto de las pocas sesiones de fotos reales del dataset, más resolución de
entrada (64x64 en vez de 48x48) para distinguir mejor siluetas parecidas, y
batch normalization para que el entrenamiento con más épocas converja mejor.

Uso:
    python -m training.entrenar_clasificador_piezas
"""
from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from backend.servicios.vision.modelo_piezas import CLASES, RedClasificadoraPiezas, preprocesar_recorte
from training.dataset_piezas import construir_dataset

RUTA_CHECKPOINT = Path("training/checkpoints/clasificador_piezas.pt")
EPOCAS = 35
TASA_APRENDIZAJE = 1e-3
TAMANO_LOTE = 64


def _augmentar(recorte_bgr: np.ndarray) -> np.ndarray:
    """Variaciones leves para no memorizar las pocas sesiones de fotos del dataset.

    Rotación pequeña (las fotos siempre son casi cenitales, no tiene sentido
    rotar mucho) + brillo y contraste al azar. Solo se aplica en entrenamiento.
    """
    alto, ancho = recorte_bgr.shape[:2]
    angulo = random.uniform(-12, 12)
    matriz_rotacion = cv2.getRotationMatrix2D((ancho / 2, alto / 2), angulo, 1.0)
    rotado = cv2.warpAffine(recorte_bgr, matriz_rotacion, (ancho, alto), borderMode=cv2.BORDER_REFLECT)

    contraste = random.uniform(0.8, 1.2)
    brillo = random.uniform(-25, 25)
    return np.clip(rotado.astype(np.float32) * contraste + brillo, 0, 255).astype(np.uint8)


class DatasetCasillas(Dataset):
    """Envuelve la lista (recorte BGR, etiqueta) como Dataset de PyTorch."""

    def __init__(self, muestras: list[tuple[np.ndarray, str]], augmentar: bool = False):
        self.muestras = muestras
        self.augmentar = augmentar
        self.indice_de_clase = {clase: i for i, clase in enumerate(CLASES)}

    def __len__(self) -> int:
        return len(self.muestras)

    def __getitem__(self, indice: int) -> tuple[torch.Tensor, int]:
        recorte, etiqueta = self.muestras[indice]
        if self.augmentar:
            recorte = _augmentar(recorte)
        tensor = preprocesar_recorte(recorte)
        return tensor, self.indice_de_clase[etiqueta]


def _pesos_por_clase(muestras: list[tuple[np.ndarray, str]]) -> torch.Tensor:
    """Peso inversamente proporcional a la frecuencia de cada clase.

    Sin esto, el modelo aprende que casi siempre acierta prediciendo "peón"
    o "vacía" y nunca se arriesga a predecir "dama" — son las que menos
    ejemplos tienen (menos de 100 de 2869 anotaciones totales).
    """
    conteos = Counter(etiqueta for _, etiqueta in muestras)
    pesos = torch.tensor([1.0 / conteos[clase] for clase in CLASES], dtype=torch.float32)
    return pesos / pesos.mean()  # normalizado para que el promedio de pesos sea 1


def _evaluar(modelo: nn.Module, cargador: DataLoader, dispositivo: str) -> float:
    modelo.eval()
    correctas, total = 0, 0
    with torch.no_grad():
        for entradas, etiquetas in cargador:
            entradas, etiquetas = entradas.to(dispositivo), etiquetas.to(dispositivo)
            predicciones = modelo(entradas).argmax(dim=1)
            correctas += (predicciones == etiquetas).sum().item()
            total += etiquetas.size(0)
    return correctas / total if total else 0.0


def entrenar() -> None:
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Usando dispositivo: {dispositivo}")

    print("Armando dataset de entrenamiento...")
    muestras_train = construir_dataset("training/dataset_tablero/train")
    print("Armando dataset de validación...")
    muestras_valid = construir_dataset("training/dataset_tablero/valid")
    print(f"Train: {len(muestras_train)} casillas — Valid: {len(muestras_valid)} casillas")

    cargador_train = DataLoader(
        DatasetCasillas(muestras_train, augmentar=True), batch_size=TAMANO_LOTE, shuffle=True
    )
    cargador_valid = DataLoader(DatasetCasillas(muestras_valid), batch_size=TAMANO_LOTE)

    modelo = RedClasificadoraPiezas().to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=TASA_APRENDIZAJE, weight_decay=1e-4)
    programador = torch.optim.lr_scheduler.StepLR(optimizador, step_size=15, gamma=0.3)
    pesos_clases = _pesos_por_clase(muestras_train).to(dispositivo)
    funcion_perdida = nn.CrossEntropyLoss(weight=pesos_clases)

    mejor_accuracy = 0.0
    RUTA_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)

    for epoca in range(1, EPOCAS + 1):
        modelo.train()
        perdida_acumulada = 0.0
        for entradas, etiquetas in cargador_train:
            entradas, etiquetas = entradas.to(dispositivo), etiquetas.to(dispositivo)
            optimizador.zero_grad()
            perdida = funcion_perdida(modelo(entradas), etiquetas)
            perdida.backward()
            optimizador.step()
            perdida_acumulada += perdida.item() * entradas.size(0)
        programador.step()

        perdida_promedio = perdida_acumulada / len(muestras_train)
        accuracy_valid = _evaluar(modelo, cargador_valid, dispositivo)
        print(f"Época {epoca:2d}/{EPOCAS} — pérdida: {perdida_promedio:.4f} — accuracy valid: {accuracy_valid:.3f}")

        if accuracy_valid > mejor_accuracy:
            mejor_accuracy = accuracy_valid
            torch.save({"pesos": modelo.state_dict(), "clases": CLASES}, RUTA_CHECKPOINT)

    print(f"Mejor accuracy de validación: {mejor_accuracy:.3f} — checkpoint en {RUTA_CHECKPOINT}")


if __name__ == "__main__":
    entrenar()
