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

from backend.servicios.vision.tablero import TAMANO_RECORTE_AMPLIADO
from backend.servicios.vision.modelo_piezas import CLASES, RedClasificadoraPiezas, preprocesar_recorte
from training.entrenar_clasificador_piezas import _augmentar
from training.reentrenar_con_dataset_propio import (
    CARPETA_DATASET_PROPIO,
    RUTA_CHECKPOINT,
    SEMILLA,
    _cargar_dataset_propio_por_foto,
    _pesos_por_clase,
)
from training.entrenar_valor import elegir_dispositivo

EPOCAS = 80
TASA_APRENDIZAJE = 1e-3
TAMANO_LOTE = 16


MINIMO_AMPLIADOS = 100
"""Con menos muestras con cuadro completo que estas se entrena con los recortes justos de siempre (ver `_cargar_ampliados`)."""


def recortes_de_cuadro(cuadro: np.ndarray, datos: dict, recorte: str) -> dict[str, np.ndarray]:
    """Los recortes de las 64 casillas de un cuadro completo con el tipo de recorte pedido (`"ampliado"` o `"volumen"`).

    `datos` es el manifiesto de la captura (esquinas y cámara). Con `"volumen"` se usa el lente de esa cámara. Lanza `ValueError` si las
    esquinas no dan una geometría válida.
    """
    from backend.servicios.vision import geometria3d
    from backend.servicios.vision.tablero import recortes_ampliados

    esquinas = np.array(datos["esquinas"], dtype=np.float32)
    if recorte == "volumen":
        alto, ancho = cuadro.shape[:2]
        return geometria3d.recortes_volumen(cuadro, esquinas[::-1], geometria3d.cargar_lente(datos.get("camara", "principal"), ancho, alto))
    return recortes_ampliados(cuadro, esquinas)


def cenital(esquinas) -> float:
    """Cuánto se ve de frente el tablero con estas 4 esquinas: 1 = cenital (lados opuestos iguales), menos = más inclinada la cámara."""
    e = np.asarray(esquinas, dtype=float)
    lados = [float(np.linalg.norm(e[i] - e[(i + 1) % 4])) for i in range(4)]
    return min(min(lados[0], lados[2]) / max(lados[0], lados[2]), min(lados[1], lados[3]) / max(lados[1], lados[3]))


def misma_posicion(esquinas_captura, esquinas_actuales, tolerancia_px: float = 40.0) -> bool:
    """Si una captura se tomó con la cámara en la misma posición que la calibración actual: ninguna esquina se corrió más de `tolerancia_px` píxeles.

    Ambas en el orden de `enderezar_tablero`. Sirve más que la fecha de la calibración: volver a marcar las esquinas de la MISMA posición cambia la fecha pero
    no la posición, y las fotos de antes siguen valiendo; moverla o girarla sí las invalida.
    """
    return float(np.abs(np.asarray(esquinas_captura, dtype=float) - np.asarray(esquinas_actuales, dtype=float)).max()) <= tolerancia_px


def _cargar_desde_cuadros(
    recorte: str = "ampliado", camaras: set[str] | None = None, desde_ms: int | None = None, min_cenital: float | None = None,
    cerca_de=None,
) -> list[tuple[np.ndarray, str, str]]:
    """`(recorte, clase, captura)` de cada casilla guardada que tiene su cuadro completo y su PNG vigente.

    `recorte` es `"ampliado"` (casilla + margen fijo) o `"volumen"` (la caja 3D de la pieza con el lente de la cámara de cada captura).
    Un PNG borrado (por «Deshacer», «Borrar clase» o a mano) deja afuera esa casilla aunque el manifiesto la siga listando. `camaras` deja solo las
    capturas de esas cámaras, `desde_ms` solo las tomadas desde esa marca de tiempo (milisegundos) y `min_cenital` solo las cuyo tablero se ve de frente (ver
    `cenital`) y `cerca_de` (esquinas actuales) solo las tomadas con la cámara en esa posición (ver `misma_posicion`): sirven para entrenar con fotos de una sola cámara, desde su posición actual o solo de las tomadas desde arriba.
    """
    import json

    from training.capturar_dataset_propio import carpeta_cuadros

    muestras = []
    for manifiesto in sorted(carpeta_cuadros().glob("*.json")):
        marca = manifiesto.stem.split("_")[0]
        if desde_ms is not None and marca.isdigit() and int(marca) < desde_ms:
            continue
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        if camaras is not None and datos.get("camara", "principal") not in camaras:
            continue
        if min_cenital is not None and cenital(datos["esquinas"]) < min_cenital:
            continue
        if cerca_de is not None and not misma_posicion(datos["esquinas"], cerca_de):
            continue
        cuadro = cv2.imread(str(manifiesto.with_suffix(".jpg")))
        if cuadro is None:
            continue
        try:
            recortes = recortes_de_cuadro(cuadro, datos, recorte)
        except ValueError:
            continue  # esquinas imposibles para la geometría: se descarta esa captura
        for casilla, clase in datos["etiquetas"].items():
            if (CARPETA_DATASET_PROPIO / clase / f"{manifiesto.stem}_{casilla}.png").exists():
                muestras.append((recortes[casilla], clase, manifiesto.stem))
    return muestras


def _cargar_ampliados() -> list[tuple[np.ndarray, str, str]]:
    return _cargar_desde_cuadros("ampliado")


def separar_por_captura(muestras: list[tuple[np.ndarray, str, str]], proporcion: float = 0.2):
    """Aparta ENTERAS ~`proporcion` de las capturas (la marca de tiempo del nombre) para validar.

    Las casillas de una misma foto del tablero lleno comparten luz, ángulo y vecinas (y las fotos de las dos cámaras de un mismo
    instante, la misma posición): si unas van a entrenamiento y otras a validación, el acierto sale inflado. Con capturas completas apartadas mide cómo anda con una foto que no vio.
    """
    import json

    from training.capturar_dataset_propio import carpeta_cuadros

    def grupo(marca: str) -> str:
        """Las fotos de varias cámaras de un mismo instante comparten `grupo` en su manifiesto (ver `capturar_foto_etiquetada`)."""
        try:
            return json.loads((carpeta_cuadros() / f"{marca}.json").read_text(encoding="utf-8")).get("grupo", marca)
        except (OSError, ValueError):
            return marca

    grupos = {m: grupo(m) for m in {m for _, _, m in muestras}}
    ids = sorted(set(grupos.values()))
    azar = random.Random(SEMILLA)
    azar.shuffle(ids)
    valid_grupos = set(ids[: max(1, int(len(ids) * proporcion))])
    train = [(i, c) for i, c, m in muestras if grupos[m] not in valid_grupos]
    valid = [(i, c) for i, c, m in muestras if grupos[m] in valid_grupos]
    return train, valid


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
    def __init__(self, muestras: list[tuple[np.ndarray, str]], augmentar: bool, tamano: int = 64):
        self.muestras, self.augmentar, self.tamano = muestras, augmentar, tamano

    def __len__(self) -> int:
        return len(self.muestras)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        recorte, clase = self.muestras[i]
        if self.augmentar:
            recorte = _augmentar_fuerte(recorte)
        return preprocesar_recorte(recorte, self.tamano), CLASES.index(clase)


def _evaluar(modelo: nn.Module, cargador: DataLoader, dispositivo) -> tuple[float, list[tuple[int, int]]]:
    modelo.eval()
    pares: list[tuple[int, int]] = []
    with torch.no_grad():
        for entradas, etiquetas in cargador:
            prediccion = modelo(entradas.to(dispositivo)).argmax(dim=1).cpu()
            pares += list(zip(etiquetas.tolist(), prediccion.tolist()))
    return (sum(a == b for a, b in pares) / len(pares) if pares else 0.0), pares


def entrenar(recorte: str = "ampliado") -> None:
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)
    torch.manual_seed(SEMILLA)
    dispositivo = elegir_dispositivo()
    con_marca = _cargar_desde_cuadros(recorte) if recorte in ("ampliado", "volumen") else []
    ampliado = len(con_marca) >= MINIMO_AMPLIADOS
    if not ampliado:
        print(f"Solo {len(con_marca)} casillas con cuadro completo para el recorte {recorte} (hacen falta {MINIMO_AMPLIADOS}): se entrena con los recortes justos.")
        con_marca = _cargar_dataset_propio_por_foto()
    tamano = TAMANO_RECORTE_AMPLIADO if ampliado else 64
    muestras = [(i, c) for i, c, _ in con_marca]
    if not muestras:
        raise FileNotFoundError(f"No hay fotos en {CARPETA_DATASET_PROPIO}/")
    print(f"Dispositivo: {dispositivo} — {len(muestras)} fotos: {dict(sorted(Counter(c for _, c in muestras).items()))}")
    train, valid = separar_por_captura(con_marca)
    print(f"Entrenamiento: {len(train)} — validación (apartada): {len(valid)}")

    cargador_train = DataLoader(_Casillas(train, True, tamano), batch_size=TAMANO_LOTE, shuffle=True)
    cargador_valid = DataLoader(_Casillas(valid, False, tamano), batch_size=TAMANO_LOTE)
    modelo = RedClasificadoraPiezas(cantidad_clases=len(CLASES), tamano=tamano).to(dispositivo)
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
    torch.save({"pesos": {k: v.cpu() for k, v in modelo.state_dict().items()}, "clases": CLASES, "tamano": tamano, "ampliado": ampliado and recorte == "ampliado", "recorte": recorte if ampliado else "justo"}, RUTA_CHECKPOINT)
    print(f"Checkpoint guardado en {RUTA_CHECKPOINT}")


if __name__ == "__main__":
    import argparse

    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument(
        "--recorte", choices=["ampliado", "volumen", "justo"], default="ampliado",
        help="con qué recorte de cada casilla entrenar: ampliado (margen fijo), volumen (caja 3D de la pieza) o justo (la casilla)",
    )
    entrenar(analizador.parse_args().recorte)
