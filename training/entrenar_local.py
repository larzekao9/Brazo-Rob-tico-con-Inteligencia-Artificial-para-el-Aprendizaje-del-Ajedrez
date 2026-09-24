"""Script para entrenar el Modelo de Ajedrez v5 localmente usando la GPU RTX 5050.

Características:
1. Detecta automáticamente la GPU NVIDIA con aceleración CUDA.
2. Si el dataset de Lichess no existe en `training/data/`, lo descarga automáticamente.
3. Extrae partidas de maestros (ELO >= 2000).
4. Entrena la arquitectura SE-ResNet de 8 bloques residuales con atención por canales.
5. GUARDA AUTOMÁTICAMENTE EL CHECKPOINT EN CADA ÉPOCA en `training/checkpoints/`,
   garantizando que nunca se pierda el progreso incluso si se suspende la laptop.
"""
from __future__ import annotations

import datetime
import os
import sys
import time
from pathlib import Path
import urllib.request

import torch
from torch.utils.data import DataLoader, Dataset

# Asegurar que el backend y training estén en el PATH
DIR_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DIR_RAIZ))

from backend.servicios.aprendizaje.modelo_jugadas import (
    NUM_CLASES,
    RedSEResNetAjedrez,
    tensor_a_entrada_red,
)
from training.data_pipeline import pgn_to_samples

URL_DATASET = "https://database.lichess.org/standard/lichess_db_standard_rated_2017-02.pgn.zst"
DIR_DATA = DIR_RAIZ / "training" / "data"
RUTA_DATASET = DIR_DATA / "lichess_db_standard_rated_2017-02.pgn.zst"
DIR_CHECKPOINTS = DIR_RAIZ / "training" / "checkpoints"


class DatasetJugadas(Dataset):
    def __init__(self, muestras):
        self.muestras = muestras

    def __len__(self):
        return len(self.muestras)

    def __getitem__(self, indice):
        tensor_posicion, etiqueta = self.muestras[indice]
        return tensor_a_entrada_red(tensor_posicion), etiqueta


def descargar_dataset_si_falta():
    DIR_DATA.mkdir(parents=True, exist_ok=True)
    if not RUTA_DATASET.exists():
        print(f"Descargando dataset de Lichess a {RUTA_DATASET} (~1.7 GB)...")
        print("Esto se realiza una sola vez. Por favor espera unos minutos.")
        urllib.request.urlretrieve(URL_DATASET, RUTA_DATASET)
        print("¡Descarga completada con éxito!")
    else:
        tam_mb = RUTA_DATASET.stat().st_size / (1024 * 1024)
        print(f"Dataset encontrado en disco ({tam_mb:.1f} MB): {RUTA_DATASET}")


def main():
    DIR_CHECKPOINTS.mkdir(parents=True, exist_ok=True)

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print("=" * 60)
    print(f"Dispositivo de entrenamiento: {dispositivo.upper()}")
    if dispositivo == "cuda":
        print(f"GPU detectada: {torch.cuda.get_device_name(0)}")
        print(f"Memoria VRAM disponible: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")
    else:
        print("AVISO: CUDA no está activo en PyTorch, corriendo en CPU.")
    print("=" * 60)

    # 1. Asegurar dataset
    descargar_dataset_si_falta()

    # 2. Extraer partidas de maestros
    LIMITE_PARTIDAS = 15000  # 15,000 partidas de maestros dan ~1.2M de posiciones
    ELO_MINIMO = 2000
    print(f"\nExtrayendo {LIMITE_PARTIDAS} partidas de maestros (ELO >= {ELO_MINIMO})...")
    t0 = time.time()
    muestras = pgn_to_samples(
        RUTA_DATASET,
        limite_partidas=LIMITE_PARTIDAS,
        elo_minimo=ELO_MINIMO,
    )
    print(f"¡Listo en {time.time() - t0:.1f}s! Total posiciones extraídas: {len(muestras)}")

    # 3. Preparar DataLoader
    import random
    random.seed(42)
    random.shuffle(muestras)
    corte = int(0.9 * len(muestras))
    muestras_train = muestras[:corte]
    muestras_val = muestras[corte:]

    batch_size = 128 if dispositivo == "cuda" else 64
    cargador_train = DataLoader(DatasetJugadas(muestras_train), batch_size=batch_size, shuffle=True)
    cargador_val = DataLoader(DatasetJugadas(muestras_val), batch_size=batch_size)

    print(f"Train: {len(muestras_train)} | Val: {len(muestras_val)} | Batch Size: {batch_size}")

    # 4. Inicializar Red SE-ResNet-8
    red = RedSEResNetAjedrez(canales=192, cantidad_bloques=8).to(dispositivo)
    optimizador = torch.optim.AdamW(red.parameters(), lr=1e-3, weight_decay=1e-4)
    CANTIDAD_EPOCAS = 25
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizador, T_max=CANTIDAD_EPOCAS)
    funcion_perdida = torch.nn.CrossEntropyLoss(label_smoothing=0.05)

    def evaluar(cargador):
        red.eval()
        correctas, total = 0, 0
        with torch.no_grad():
            for entradas, etiquetas in cargador:
                entradas, etiquetas = entradas.to(dispositivo), etiquetas.to(dispositivo)
                predicciones = red(entradas).argmax(dim=1)
                correctas += (predicciones == etiquetas).sum().item()
                total += etiquetas.size(0)
        return correctas / total if total else 0.0

    mejor_acc = 0.0
    fecha_hoy = datetime.date.today().isoformat()

    print("\nIniciando entrenamiento...")
    for epoca in range(1, CANTIDAD_EPOCAS + 1):
        t_epoca = time.time()
        red.train()
        perdida_acumulada = 0.0
        for entradas, etiquetas in cargador_train:
            entradas, etiquetas = entradas.to(dispositivo), etiquetas.to(dispositivo)
            optimizador.zero_grad()
            salida = red(entradas)
            perdida = funcion_perdida(salida, etiquetas)
            perdida.backward()
            optimizador.step()
            perdida_acumulada += perdida.item() * entradas.size(0)

        scheduler.step()
        perdida_prom = perdida_acumulada / len(muestras_train)
        acc_val = evaluar(cargador_val)
        duracion = time.time() - t_epoca

        print(
            f"Época {epoca:02d}/{CANTIDAD_EPOCAS} — Pérdida: {perdida_prom:.4f} — "
            f"Val Accuracy: {acc_val:.2%} — Tiempo: {duracion:.1f}s"
        )

        # GUARDADO BLINDADO: Se guarda automáticamente al finalizar CADA época
        ruta_epoca = DIR_CHECKPOINTS / f"modelo_jugadas_v5_epoca_{epoca}.pt"
        torch.save(
            {
                "state_dict": red.state_dict(),
                "num_clases": NUM_CLASES,
                "arquitectura": "se_resnet",
                "canales": 192,
                "cantidad_bloques": 8,
                "epoca": epoca,
                "accuracy_val": acc_val,
                "fecha": fecha_hoy,
            },
            ruta_epoca,
        )

        if acc_val > mejor_acc:
            mejor_acc = acc_val
            ruta_mejor = DIR_CHECKPOINTS / "modelo_jugadas_v5_mejor.pt"
            torch.save(
                {
                    "state_dict": red.state_dict(),
                    "num_clases": NUM_CLASES,
                    "arquitectura": "se_resnet",
                    "canales": 192,
                    "cantidad_bloques": 8,
                    "epoca": epoca,
                    "accuracy_val": acc_val,
                    "fecha": fecha_hoy,
                },
                ruta_mejor,
            )
            print(f"  ⭐ ¡Nuevo récord de precisión! Checkpoint actualizado en: {ruta_mejor.name}")

    print("\n" + "=" * 60)
    print(f"¡Entrenamiento local completado! Mejor precisión de validación: {mejor_acc:.2%}")
    print(f"Modelo final guardado en: {DIR_CHECKPOINTS / 'modelo_jugadas_v5_mejor.pt'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
