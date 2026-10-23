"""Entrena un modelo CANDIDATO de piezas con el dataset propio (incluidas las casillas corregidas en el probador) y solo reemplaza al actual si lo supera.

Pensado para el botón «Entrenar con mis correcciones» del probador: usa la GPU del Mac (MPS) si hay (ver `elegir_dispositivo`). Los dos
modelos, el actual (`clasificador_piezas.pt`, del formato que sea: red propia o TorchScript de Colab) y el candidato, se miden sobre las MISMAS
capturas apartadas para validar. Las muestras corregidas siempre entran a entrenamiento (se repiten `REPETICIONES_CORRECCION` veces porque son
pocas) y nunca a validación: lo que se compara es qué tan bien reconocen fotos que ninguno vio. Si el candidato gana, el actual se guarda como
`clasificador_piezas.anterior_<fecha>.pt` y el candidato pasa a ser el modelo; si no, el actual queda intacto. El candidato se guarda siempre en
`clasificador_piezas.candidato.pt`. La última línea de la salida es `RESULTADO: reemplazado ...` o `RESULTADO: conservado ...`.

Uso:
    python -m training.entrenar_candidato
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
from training.capturar_dataset_propio import carpeta_ampliados
from training.entrenar_piezas_propio import MINIMO_AMPLIADOS, _cargar_desde_cuadros, _Casillas, _evaluar, separar_por_captura
from training.entrenar_valor import elegir_dispositivo
from training.reentrenar_con_dataset_propio import RUTA_CHECKPOINT, SEMILLA, _pesos_por_clase

RUTA_CANDIDATO = RUTA_CHECKPOINT.with_name("clasificador_piezas.candidato.pt")
PREFIJO_CORRECCION = "corr"
REPETICIONES_CORRECCION = 5
EPOCAS = 50
TASA_APRENDIZAJE = 1e-3
TAMANO_LOTE = 32


def cargar_correcciones() -> list[tuple[np.ndarray, str]]:
    """`(recorte ampliado, clase)` de cada casilla corregida en el probador (`<dataset>_ampliado/<clase>/corr<ms>_<camara>_<casilla>.png`)."""
    raiz = carpeta_ampliados()
    muestras = []
    for archivo in sorted(raiz.glob(f"*/{PREFIJO_CORRECCION}*.png")):
        recorte = cv2.imread(str(archivo))
        if recorte is not None and archivo.parent.name in CLASES:
            muestras.append((recorte, archivo.parent.name))
    return muestras


def exactitud_del_modelo_actual(valid: list[tuple[np.ndarray, str]], dispositivo: str = "cpu") -> float | None:
    """Acierto del modelo guardado en `RUTA_CHECKPOINT` (de cualquier formato) sobre `valid`, con su propio tamaño de entrada. `None` si no hay."""
    if not RUTA_CHECKPOINT.exists():
        return None
    punto = torch.load(RUTA_CHECKPOINT, map_location="cpu", weights_only=False)
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


def entrenar_candidato() -> None:
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)
    torch.manual_seed(SEMILLA)
    dispositivo = elegir_dispositivo()
    print(f"Dispositivo de entrenamiento: {dispositivo}")
    con_marca = _cargar_desde_cuadros("ampliado")
    if len(con_marca) < MINIMO_AMPLIADOS:
        raise ValueError(f"Hacen falta al menos {MINIMO_AMPLIADOS} casillas con cuadro completo (hay {len(con_marca)}): sacá más fotos del tablero")
    correcciones = cargar_correcciones()
    train, valid = separar_por_captura(con_marca)
    train = train + correcciones * REPETICIONES_CORRECCION
    print(f"Entrenamiento: {len(train)} ({len(correcciones)} corregidas, x{REPETICIONES_CORRECCION}) — validación apartada: {len(valid)}")
    por_clase = dict(sorted(Counter(c for _, c in train).items()))
    print(f"Muestras por clase: {por_clase}")

    cargador_train = DataLoader(_Casillas(train, True, TAMANO_RECORTE_AMPLIADO), batch_size=TAMANO_LOTE, shuffle=True)
    cargador_valid = DataLoader(_Casillas(valid, False, TAMANO_RECORTE_AMPLIADO), batch_size=TAMANO_LOTE)
    modelo = RedClasificadoraPiezas(cantidad_clases=len(CLASES), tamano=TAMANO_RECORTE_AMPLIADO).to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=TASA_APRENDIZAJE, weight_decay=1e-4)
    perdida_fn = nn.CrossEntropyLoss(weight=_pesos_por_clase(train).to(dispositivo))

    mejor, mejores_pesos = -1.0, None
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
        if exactitud >= mejor:
            mejor, mejores_pesos = exactitud, {k: v.detach().cpu().clone() for k, v in modelo.state_dict().items()}
        print(f"Época {epoca}/{EPOCAS} — pérdida {total / len(train):.4f} — validación {exactitud:.3f} (mejor {mejor:.3f}) — {time.monotonic() - inicio:.0f} s", flush=True)

    modelo.load_state_dict(mejores_pesos)
    RUTA_CANDIDATO.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"pesos": mejores_pesos, "clases": CLASES, "tamano": TAMANO_RECORTE_AMPLIADO, "ampliado": True, "recorte": "ampliado", "exactitud_validacion": round(mejor, 4)},
        RUTA_CANDIDATO,
    )
    actual = exactitud_del_modelo_actual(valid)
    print(f"Candidato: {mejor:.3f} — modelo actual: {'sin modelo' if actual is None else f'{actual:.3f}'} (mismas {len(valid)} casillas apartadas)")
    if actual is not None and mejor <= actual:
        print(f"RESULTADO: conservado — el candidato ({mejor:.1%}) no supera al actual ({actual:.1%}); queda guardado en {RUTA_CANDIDATO.name}")
        return
    if RUTA_CHECKPOINT.exists():
        shutil.copy(RUTA_CHECKPOINT, RUTA_CHECKPOINT.with_name(f"clasificador_piezas.anterior_{time.strftime('%Y%m%d_%H%M%S')}.pt"))
    shutil.copy(RUTA_CANDIDATO, RUTA_CHECKPOINT)
    RUTA_CHECKPOINT.with_suffix(".json").unlink(missing_ok=True)  # la ficha del modelo de Colab ya no describe al nuevo
    print(f"RESULTADO: reemplazado — el candidato ({mejor:.1%}) supera al actual ({'sin modelo' if actual is None else f'{actual:.1%}'}); el anterior quedó respaldado")


if __name__ == "__main__":
    entrenar_candidato()
