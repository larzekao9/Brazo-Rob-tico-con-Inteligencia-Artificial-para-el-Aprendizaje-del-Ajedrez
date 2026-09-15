"""Reentrena el clasificador de piezas sumando fotos reales de TU tablero.

Parte del checkpoint ya entrenado (`training/checkpoints/clasificador_piezas.pt`)
en vez de empezar de cero — es fine-tuning, no un entrenamiento nuevo: el
modelo ya sabe reconocer formas de piezas en general (por el dataset de
Roboflow), solo necesita adaptarse a los colores/estilo de este tablero
puntual. Por eso la tasa de aprendizaje es más chica que en
`entrenar_clasificador_piezas.py`.

Entrena con la mezcla de ambos datasets (Roboflow + el propio) para no
"olvidar" lo aprendido en el dataset original mientras se adapta al nuevo —
un riesgo real de hacer fine-tuning solo con las fotos nuevas, que además
son muchas menos.

El checkpoint se guarda según el accuracy contra un recorte apartado de TUS
propias fotos (no contra el dataset de Roboflow) — es lo único que mide lo
que realmente importa acá: que reconozca tu tablero. El accuracy contra
Roboflow se sigue mostrando, pero solo como diagnóstico para detectar si el
modelo está "olvidando" el dataset original, no para decidir si guardar.

Requiere haber corrido `training/capturar_dataset_propio.py` varias veces
antes (con distintos ángulos/posiciones) para tener algo en
`training/dataset_propio/`.

Uso:
    python -m training.reentrenar_con_dataset_propio
"""
from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

import cv2
import torch
from torch import nn
from torch.utils.data import DataLoader

from backend.servicios.vision.modelo_piezas import CLASES, RedClasificadoraPiezas
from training.dataset_piezas import construir_dataset
from training.entrenar_clasificador_piezas import DatasetCasillas, _evaluar

RUTA_CHECKPOINT = Path("training/checkpoints/clasificador_piezas.pt")
CARPETA_DATASET_PROPIO = Path("training/dataset_propio")
EPOCAS = 20
TASA_APRENDIZAJE = 1e-4  # más chica que el entrenamiento original: es fine-tuning
TAMANO_LOTE = 32
PROPORCION_VALIDACION_PROPIA = 0.2
SEMILLA = 42


def _cargar_dataset_propio() -> list[tuple[cv2.typing.MatLike, str]]:
    muestras = []
    for carpeta_clase in sorted(CARPETA_DATASET_PROPIO.iterdir()):
        if not carpeta_clase.is_dir():
            continue
        clase = carpeta_clase.name
        for ruta_imagen in carpeta_clase.glob("*.png"):
            recorte = cv2.imread(str(ruta_imagen))
            if recorte is not None:
                muestras.append((recorte, clase))
    return muestras


def _separar_train_valid(
    muestras: list[tuple[cv2.typing.MatLike, str]], proporcion_valid: float
) -> tuple[list[tuple[cv2.typing.MatLike, str]], list[tuple[cv2.typing.MatLike, str]]]:
    """Separa un recorte de validación por clase (no simplemente al azar del total),

    para que una clase con pocos ejemplos (ej. rey) no quede sin ningún
    ejemplo de validación solo por mala suerte del sorteo.
    """
    aleatorio = random.Random(SEMILLA)
    por_clase: dict[str, list[tuple[cv2.typing.MatLike, str]]] = {}
    for muestra in muestras:
        por_clase.setdefault(muestra[1], []).append(muestra)

    train: list[tuple[cv2.typing.MatLike, str]] = []
    valid: list[tuple[cv2.typing.MatLike, str]] = []
    for muestras_clase in por_clase.values():
        aleatorio.shuffle(muestras_clase)
        corte = max(1, int(len(muestras_clase) * proporcion_valid))
        valid += muestras_clase[:corte]
        train += muestras_clase[corte:]
    return train, valid


def _pesos_por_clase(muestras: list[tuple[cv2.typing.MatLike, str]]) -> torch.Tensor:
    conteos = Counter(etiqueta for _, etiqueta in muestras)
    pesos = torch.tensor([1.0 / conteos.get(clase, 1) for clase in CLASES], dtype=torch.float32)
    return pesos / pesos.mean()


def reentrenar() -> None:
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Usando dispositivo: {dispositivo}")

    if not RUTA_CHECKPOINT.exists():
        raise FileNotFoundError(
            f"No se encontró {RUTA_CHECKPOINT} — correr primero "
            "`python -m training.entrenar_clasificador_piezas`"
        )
    if not CARPETA_DATASET_PROPIO.exists() or not any(CARPETA_DATASET_PROPIO.iterdir()):
        raise FileNotFoundError(
            f"No hay nada en {CARPETA_DATASET_PROPIO}/ — correr primero "
            "`python -m training.capturar_dataset_propio \"<fen>\"` varias veces"
        )

    print("Armando dataset original (Roboflow)...")
    muestras_originales = construir_dataset("training/dataset_tablero/train")
    print("Armando dataset propio...")
    muestras_propias = _cargar_dataset_propio()
    print(f"Original: {len(muestras_originales)} casillas — Propio: {len(muestras_propias)} casillas")
    if len(muestras_propias) < 20:
        print(
            "Aviso: muy pocas muestras propias todavía — el resultado va a mejorar poco. "
            "Conviene correr capturar_dataset_propio.py varias veces más antes de esto."
        )

    muestras_propias_train, muestras_propias_valid = _separar_train_valid(
        muestras_propias, PROPORCION_VALIDACION_PROPIA
    )
    print(
        f"Propio train: {len(muestras_propias_train)} — "
        f"Propio valid (apartado, no se entrena con esto): {len(muestras_propias_valid)}"
    )

    muestras_train = muestras_originales + muestras_propias_train
    muestras_valid_roboflow = construir_dataset("training/dataset_tablero/valid")

    cargador_train = DataLoader(
        DatasetCasillas(muestras_train, augmentar=True), batch_size=TAMANO_LOTE, shuffle=True
    )
    cargador_valid_roboflow = DataLoader(DatasetCasillas(muestras_valid_roboflow), batch_size=TAMANO_LOTE)
    cargador_valid_propio = DataLoader(DatasetCasillas(muestras_propias_valid), batch_size=TAMANO_LOTE)

    checkpoint = torch.load(RUTA_CHECKPOINT, map_location=dispositivo, weights_only=False)
    modelo = RedClasificadoraPiezas(cantidad_clases=len(checkpoint["clases"])).to(dispositivo)
    modelo.load_state_dict(checkpoint["pesos"])

    optimizador = torch.optim.Adam(modelo.parameters(), lr=TASA_APRENDIZAJE, weight_decay=1e-4)
    pesos_clases = _pesos_por_clase(muestras_train).to(dispositivo)
    funcion_perdida = nn.CrossEntropyLoss(weight=pesos_clases)

    mejor_accuracy_propio = _evaluar(modelo, cargador_valid_propio, dispositivo)
    accuracy_roboflow_inicial = _evaluar(modelo, cargador_valid_roboflow, dispositivo)
    print(
        f"Antes de reentrenar — accuracy en TU tablero (lo que importa): {mejor_accuracy_propio:.3f} "
        f"— accuracy en Roboflow (diagnóstico): {accuracy_roboflow_inicial:.3f}"
    )

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

        perdida_promedio = perdida_acumulada / len(muestras_train)
        accuracy_propio = _evaluar(modelo, cargador_valid_propio, dispositivo)
        accuracy_roboflow = _evaluar(modelo, cargador_valid_roboflow, dispositivo)
        print(
            f"Época {epoca:2d}/{EPOCAS} — pérdida: {perdida_promedio:.4f} — "
            f"tu tablero: {accuracy_propio:.3f} — Roboflow: {accuracy_roboflow:.3f}"
        )

        if accuracy_propio >= mejor_accuracy_propio:
            mejor_accuracy_propio = accuracy_propio
            torch.save({"pesos": modelo.state_dict(), "clases": checkpoint["clases"]}, RUTA_CHECKPOINT)

    print(f"Checkpoint actualizado en {RUTA_CHECKPOINT} — accuracy en tu tablero: {mejor_accuracy_propio:.3f}")


if __name__ == "__main__":
    reentrenar()
