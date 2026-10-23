"""Entrena la red de valor de Turing con evaluaciones de Lichess y la compara con la evaluación manual de la búsqueda.

Mide, sobre posiciones que la red NO vio, qué tan bien predice el valor que dio un motor fuerte (error cuadrático y correlación)
y con qué frecuencia acierta quién va ganando en posiciones claras. Hace lo mismo con la evaluación manual de material y
posición (`busqueda_turing.evaluar`): ese es el número a superar para que valga la pena usar la red en la búsqueda.

Uso (en Colab con GPU o local):
    python -m training.entrenar_valor --datos training/dataset_valor/valor_1m.npz --epocas 8 --salida training/checkpoints/valor_v1.pt
"""
from __future__ import annotations

import argparse
import math
import os
import time
from pathlib import Path

import chess
import numpy as np
import torch
import torch.nn.functional as F

from backend.servicios.aprendizaje.busqueda_turing import evaluar
from backend.servicios.aprendizaje.modelo_valor import RedValor
from training.datos_valor import ESCALA_CP

PROPORCION_VALIDACION = 0.03
UMBRAL_POSICION_CLARA = 0.25
"""|valor| desde el cual una posición se considera clara (≈ 105 cp): ahí se mide si se acierta quién va ganando."""


def elegir_dispositivo() -> str:
    """`"cuda"` o `"mps"` (GPU del Mac) solo si la GPU de verdad puede correr la red; si no (por ejemplo una placa nueva sin kernels en esta
    versión de torch: `no kernel image`), `"cpu"`. Con `ENTRENAR_EN_CPU=1` siempre `"cpu"`."""
    if os.environ.get("ENTRENAR_EN_CPU") == "1":
        return "cpu"
    for dispositivo, disponible in (("cuda", torch.cuda.is_available()), ("mps", torch.backends.mps.is_available())):
        if not disponible:
            continue
        try:
            torch.nn.functional.conv2d(torch.zeros(1, 1, 3, 3, device=dispositivo), torch.zeros(1, 1, 3, 3, device=dispositivo))
            return dispositivo
        except RuntimeError:
            continue
    return "cpu"


def a_entrada(posiciones: np.ndarray) -> torch.Tensor:
    """(N, 8, 8, 12) `uint8` → (N, 12, 8, 8) `float32`, el mismo formato que usa la red de política."""
    return torch.from_numpy(posiciones).permute(0, 3, 1, 2).float()


def metricas(prediccion: np.ndarray, objetivo: np.ndarray) -> dict[str, float]:
    """Error cuadrático medio, correlación de Pearson y acierto del signo en posiciones claras."""
    error = float(np.mean((prediccion - objetivo) ** 2))
    correlacion = float(np.corrcoef(prediccion, objetivo)[0, 1]) if prediccion.std() > 0 and objetivo.std() > 0 else 0.0
    claras = np.abs(objetivo) >= UMBRAL_POSICION_CLARA
    acierto = float(np.mean(np.sign(prediccion[claras]) == np.sign(objetivo[claras]))) if claras.any() else float("nan")
    return {"error_cuadratico": error, "correlacion": correlacion, "acierto_signo_claras": acierto}


def valor_de_evaluacion_manual(posiciones: np.ndarray) -> np.ndarray:
    """Valor en [-1, 1] que daría la evaluación manual de la búsqueda (`evaluar`, desde quien mueve), para compararla."""
    valores = np.empty(len(posiciones), dtype=np.float32)
    simbolos = "PNBRQKpnbrqk"
    for i, plano in enumerate(posiciones):
        tablero = chess.Board(None)
        for canal in range(12):
            for fila, columna in zip(*np.nonzero(plano[:, :, canal])):
                tablero.set_piece_at(chess.square(int(columna), int(fila)), chess.Piece.from_symbol(simbolos[canal]))
        valores[i] = math.tanh(evaluar(tablero) / ESCALA_CP)
    return valores


def entrenar(
    datos: str | Path, epocas: int, salida: str | Path, canales: int = 64, bloques: int = 4, lote: int = 512, tasa: float = 2e-3
) -> dict:
    """Entrena la red de valor, guarda el mejor checkpoint (por error de validación) y devuelve las métricas."""
    archivo = np.load(datos)
    posiciones, objetivos = archivo["posiciones"], archivo["valores"]
    rng = np.random.default_rng(0)
    orden = rng.permutation(len(objetivos))
    cantidad_val = max(1, int(len(orden) * PROPORCION_VALIDACION))
    val, ent = orden[:cantidad_val], orden[cantidad_val:]

    dispositivo = elegir_dispositivo()
    modelo = RedValor(canales, bloques).to(dispositivo)
    optimizador = torch.optim.AdamW(modelo.parameters(), lr=tasa, weight_decay=1e-4)
    pasos = epocas * math.ceil(len(ent) / lote)
    planificador = torch.optim.lr_scheduler.OneCycleLR(optimizador, max_lr=tasa, total_steps=pasos, pct_start=0.1)
    escalador = torch.amp.GradScaler(enabled=dispositivo == "cuda")

    x_val, y_val = a_entrada(posiciones[val]), objetivos[val]
    mejor = {"error_cuadratico": float("inf")}
    for epoca in range(1, epocas + 1):
        modelo.train()
        inicio = time.time()
        for indices in np.array_split(rng.permutation(ent), math.ceil(len(ent) / lote)):
            x = a_entrada(posiciones[np.sort(indices)]).to(dispositivo)
            y = torch.from_numpy(objetivos[np.sort(indices)]).to(dispositivo)
            with torch.autocast(device_type=dispositivo, enabled=dispositivo == "cuda"):
                perdida = F.mse_loss(modelo(x).float(), y)
            optimizador.zero_grad(set_to_none=True)
            escalador.scale(perdida).backward()
            escalador.step(optimizador)
            escalador.update()
            planificador.step()
        modelo.eval()
        with torch.no_grad():
            prediccion = torch.cat([modelo(x_val[i:i + 4096].to(dispositivo)).float().cpu() for i in range(0, len(x_val), 4096)]).numpy()
        resultado = metricas(prediccion, y_val)
        print(f"época {epoca}/{epocas}  error {resultado['error_cuadratico']:.4f}  correlación {resultado['correlacion']:.3f}  "
              f"acierto en claras {resultado['acierto_signo_claras']:.1%}  ({time.time() - inicio:.0f}s)", flush=True)
        if resultado["error_cuadratico"] < mejor["error_cuadratico"]:
            mejor = resultado
            Path(salida).parent.mkdir(parents=True, exist_ok=True)
            torch.save({"state_dict": {k: v.cpu() for k, v in modelo.state_dict().items()}, "canales": canales, "bloques": bloques, "metricas": resultado}, salida)

    manual = metricas(valor_de_evaluacion_manual(posiciones[val]), y_val)
    print("\nMismas posiciones de validación:")
    print(f"  evaluación manual (la de hoy): error {manual['error_cuadratico']:.4f}  correlación {manual['correlacion']:.3f}  acierto en claras {manual['acierto_signo_claras']:.1%}")
    print(f"  red de valor (mejor época):    error {mejor['error_cuadratico']:.4f}  correlación {mejor['correlacion']:.3f}  acierto en claras {mejor['acierto_signo_claras']:.1%}")
    return {"red": mejor, "manual": manual}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datos", default="training/dataset_valor/valor.npz")
    parser.add_argument("--salida", default="training/checkpoints/valor_v1.pt")
    parser.add_argument("--epocas", type=int, default=8)
    parser.add_argument("--canales", type=int, default=64)
    parser.add_argument("--bloques", type=int, default=4)
    args = parser.parse_args()
    entrenar(args.datos, args.epocas, args.salida, args.canales, args.bloques)


if __name__ == "__main__":
    main()
