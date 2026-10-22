"""Entrena el clasificador de piezas que mira las DOS cámaras a la vez (`modelo_piezas.RedDosVistas`).

Cada muestra es una casilla de un mismo instante (`grupo` del manifiesto): el recorte de la cámara principal y el de la secundaria con su etiqueta.
Las casillas que solo tienen una vista (capturas con una sola cámara) también entran, con la otra vista anulada, y además se quita una vista al
azar a algunas muestras con las dos: así el modelo sirve igual si más tarde falta una cámara. Se valida con grupos enteros apartados (nunca
queda un mismo instante a los dos lados). Guarda `training/checkpoints/clasificador_piezas_dos_vistas.pt`.

Uso:
    python -m training.entrenar_dos_vistas [--recorte ampliado|volumen]
"""
from __future__ import annotations

import json
import random
from collections import Counter

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from backend.servicios.vision.modelo_piezas import CLASES, TAMANO_ENTRADA, RedDosVistas, preprocesar_recorte
from backend.servicios.vision.piezas import RANURAS, RUTA_DOS_VISTAS
from backend.servicios.vision.tablero import TAMANO_RECORTE_AMPLIADO
from training.entrenar_piezas_propio import _augmentar_fuerte, recortes_de_cuadro
from training.entrenar_valor import elegir_dispositivo
from training.reentrenar_con_dataset_propio import CARPETA_DATASET_PROPIO, SEMILLA

EPOCAS = 80
TAMANO_LOTE = 16
PROBABILIDAD_QUITAR_VISTA = 0.25
MINIMO_MUESTRAS = 60


def cargar_muestras(recorte: str) -> list[dict]:
    """Una muestra por casilla de cada instante: `{grupo, clase, vistas: {camara: recorte}}`, solo con casillas cuyo PNG sigue vigente."""
    from training.capturar_dataset_propio import carpeta_cuadros

    por_clave: dict[tuple[str, str], dict] = {}
    for manifiesto in sorted(carpeta_cuadros().glob("*.json")):
        cuadro = cv2.imread(str(manifiesto.with_suffix(".jpg")))
        if cuadro is None:
            continue
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        camara = datos.get("camara", "principal")
        if camara not in RANURAS:
            continue
        try:
            recortes = recortes_de_cuadro(cuadro, datos, recorte)
        except ValueError:
            continue
        grupo = datos.get("grupo", manifiesto.stem)
        for casilla, clase in datos["etiquetas"].items():
            if not (CARPETA_DATASET_PROPIO / clase / f"{manifiesto.stem}_{casilla}.png").exists():
                continue
            muestra = por_clave.setdefault((grupo, casilla), {"grupo": grupo, "clase": clase, "vistas": {}})
            muestra["vistas"][camara] = recortes[casilla]
    return list(por_clave.values())


def separar_por_grupo(muestras: list[dict], proporcion: float = 0.2) -> tuple[list[dict], list[dict]]:
    grupos = sorted({m["grupo"] for m in muestras})
    azar = random.Random(SEMILLA)
    azar.shuffle(grupos)
    validos = set(grupos[: max(1, int(len(grupos) * proporcion))])
    return [m for m in muestras if m["grupo"] not in validos], [m for m in muestras if m["grupo"] in validos]


class _Casillas(Dataset):
    def __init__(self, muestras: list[dict], augmentar: bool, tamano: int):
        self.muestras, self.augmentar, self.tamano = muestras, augmentar, tamano

    def __len__(self) -> int:
        return len(self.muestras)

    def __getitem__(self, i: int):
        muestra = self.muestras[i]
        vistas = dict(muestra["vistas"])
        if self.augmentar and len(vistas) == 2 and random.random() < PROBABILIDAD_QUITAR_VISTA:
            vistas.pop(random.choice(list(vistas)))
        tensores = [torch.zeros(3, self.tamano, self.tamano), torch.zeros(3, self.tamano, self.tamano)]
        mascara = torch.zeros(2)
        for camara, recorte in vistas.items():
            ranura = RANURAS[camara]
            tensores[ranura] = preprocesar_recorte(_augmentar_fuerte(recorte) if self.augmentar else recorte, self.tamano)
            mascara[ranura] = 1.0
        return tensores[0], tensores[1], mascara, CLASES.index(muestra["clase"])


def _evaluar(modelo: nn.Module, cargador: DataLoader, dispositivo) -> tuple[float, list[tuple[int, int, int]]]:
    modelo.eval()
    resultados = []
    with torch.no_grad():
        for a, b, mascara, y in cargador:
            prediccion = modelo(a.to(dispositivo), b.to(dispositivo), mascara.to(dispositivo)).argmax(1).cpu()
            resultados += list(zip(y.tolist(), prediccion.tolist(), mascara.sum(1).int().tolist()))
    return (sum(r == p for r, p, _ in resultados) / len(resultados) if resultados else 0.0), resultados


def entrenar(recorte: str = "ampliado") -> None:
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)
    torch.manual_seed(SEMILLA)
    dispositivo = elegir_dispositivo()
    muestras = cargar_muestras(recorte)
    pares = sum(1 for m in muestras if len(m["vistas"]) == 2)
    print(f"{len(muestras)} casillas ({pares} con las dos cámaras) con recorte {recorte}: {dict(sorted(Counter(m['clase'] for m in muestras).items()))}")
    if len(muestras) < MINIMO_MUESTRAS:
        raise ValueError(f"Hacen falta al menos {MINIMO_MUESTRAS} casillas con cuadro completo (hay {len(muestras)}): sacá fotos con las dos cámaras calibradas")
    tamano = TAMANO_RECORTE_AMPLIADO if recorte in ("ampliado", "volumen") else TAMANO_ENTRADA
    train, valid = separar_por_grupo(muestras)
    pesos = torch.tensor([1.0 / max(1, Counter(m["clase"] for m in train)[c]) for c in CLASES])
    pesos = (pesos / pesos.mean()).to(dispositivo)
    modelo = RedDosVistas(cantidad_clases=len(CLASES), tamano=tamano).to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=1e-3, weight_decay=1e-4)
    perdida_fn = nn.CrossEntropyLoss(weight=pesos)
    cargador = DataLoader(_Casillas(train, True, tamano), batch_size=TAMANO_LOTE, shuffle=True)
    cargador_valid = DataLoader(_Casillas(valid, False, tamano), batch_size=TAMANO_LOTE)
    print(f"Entrenamiento: {len(train)} — validación (grupos apartados): {len(valid)}")
    mejor, mejores_pesos = -1.0, None
    for epoca in range(1, EPOCAS + 1):
        modelo.train()
        for a, b, mascara, y in cargador:
            optimizador.zero_grad()
            perdida_fn(modelo(a.to(dispositivo), b.to(dispositivo), mascara.to(dispositivo)), y.to(dispositivo)).backward()
            optimizador.step()
        exactitud, _ = _evaluar(modelo, cargador_valid, dispositivo)
        if exactitud >= mejor:
            mejor, mejores_pesos = exactitud, {k: v.detach().cpu().clone() for k, v in modelo.state_dict().items()}
        if epoca % 10 == 0 or epoca == 1:
            print(f"Época {epoca:3d}/{EPOCAS} — validación {exactitud:.3f}")
    modelo.load_state_dict(mejores_pesos)
    exactitud, resultados = _evaluar(modelo, cargador_valid, dispositivo)
    print(f"Mejor validación: {exactitud:.3f}")
    for vistas, nombre in ((2, "con las dos cámaras"), (1, "con una sola")):
        grupo = [(r, p) for r, p, v in resultados if v == vistas]
        if grupo:
            print(f"  {nombre}: {sum(r == p for r, p in grupo) / len(grupo):.3f} ({len(grupo)} casillas)")
    for (real, pred), n in Counter((CLASES[r], CLASES[p]) for r, p, _ in resultados if r != p).most_common(8):
        print(f"  confundió {real} con {pred}: {n}")
    RUTA_DOS_VISTAS.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"pesos": {k: v.cpu() for k, v in modelo.state_dict().items()}, "clases": CLASES, "tamano": tamano, "recorte": recorte, "tipo": "dos_vistas",
         "clases_entrenadas": sorted({m["clase"] for m in train}), "exactitud": round(float(exactitud), 4)},
        RUTA_DOS_VISTAS,
    )
    print(f"Guardado en {RUTA_DOS_VISTAS}")


if __name__ == "__main__":
    import argparse

    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--recorte", choices=["ampliado", "volumen"], default="ampliado")
    entrenar(analizador.parse_args().recorte)
