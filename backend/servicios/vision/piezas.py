"""Clasifica qué pieza hay en el recorte de una casilla (HU1, segunda etapa).

Carga el checkpoint entrenado por `training/entrenar_clasificador_piezas.py`
una sola vez (perezoso, en el primer llamado) y lo reusa para el resto de la
ejecución del backend.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from backend.servicios.vision.modelo_piezas import TAMANO_ENTRADA, RedClasificadoraPiezas, RedDosVistas, preprocesar_recorte

RUTA_CHECKPOINT = Path("training/checkpoints/clasificador_piezas.pt")

_modelo: RedClasificadoraPiezas | None = None
_clases: list[str] | None = None
_tamano: int = TAMANO_ENTRADA
_ampliado: bool = False
_recorte: str = "justo"


def cargar_red(checkpoint: dict, tamano: int) -> torch.nn.Module:
    """La red de un checkpoint del clasificador de piezas, lista para inferir (en modo evaluación).

    Dos formatos: el de siempre (`pesos` de `RedClasificadoraPiezas`) y el que sale de Colab (`training/colab_vision_piezas.ipynb`), con
    `formato: "torchscript"` y la red completa en `torchscript` (bytes). Ese trae la normalización adentro y recibe lo mismo que la otra (RGB
    de 0 a 1, `tamano` × `tamano`, ver `preprocesar_recorte`), así que se puede usar una red preentrenada sin instalar torchvision.
    """
    if checkpoint.get("formato") == "torchscript":
        import io

        red = torch.jit.load(io.BytesIO(checkpoint["torchscript"]), map_location="cpu")
    else:
        red = RedClasificadoraPiezas(cantidad_clases=len(checkpoint["clases"]), tamano=tamano)
        red.load_state_dict(checkpoint["pesos"])
    red.eval()
    return red


def _cargar_modelo() -> tuple[torch.nn.Module, list[str]]:
    global _modelo, _clases, _tamano, _ampliado, _recorte
    if _modelo is None:
        if not RUTA_CHECKPOINT.exists():
            raise FileNotFoundError(
                f"No se encontró {RUTA_CHECKPOINT} — correr antes "
                "`python -m training.entrenar_clasificador_piezas`"
            )
        checkpoint = torch.load(RUTA_CHECKPOINT, map_location="cpu", weights_only=False)
        _clases = checkpoint["clases"]
        _tamano = int(checkpoint.get("tamano", TAMANO_ENTRADA))
        _ampliado = bool(checkpoint.get("ampliado", checkpoint.get("recorte") == "ampliado"))
        _recorte = checkpoint.get("recorte") or ("ampliado" if _ampliado else "justo")
        _modelo = cargar_red(checkpoint, _tamano)
    return _modelo, _clases


def modo_recorte() -> str:
    """Con qué recorte se entrenó el modelo cargado: `"justo"` (la casilla), `"ampliado"` (casilla + margen fijo) o `"volumen"` (la caja 3D de la pieza)."""
    _cargar_modelo()
    return _recorte


def usa_recorte_ampliado() -> bool:
    """Si el modelo cargado se entrenó con el recorte ampliado de cada casilla (`tablero.recortes_ampliados`) y no con el justo."""
    _cargar_modelo()
    return _ampliado


RUTA_DOS_VISTAS = Path("training/checkpoints/clasificador_piezas_dos_vistas.pt")
RANURAS = {"principal": 0, "secundaria": 1}
_dos: tuple | None = None
_dos_buscado = False
_dos_motivo: str | None = None
MINIMO_CLASES_DOS_VISTAS = 12
"""Un modelo de dos vistas solo se usa si en el entrenamiento vio al menos estas clases (de 13): uno entrenado con pocas piezas reconocería mal
las que nunca vio y, como reemplaza al de una vista, empeoraría el reconocimiento."""


def _cargar_dos_vistas() -> tuple | None:
    """`(red, clases, tamano, recorte)` del modelo de dos vistas, o `None` si todavía no se entrenó (se busca una sola vez)."""
    global _dos, _dos_buscado, _dos_motivo
    if not _dos_buscado:
        _dos_buscado = True
        if RUTA_DOS_VISTAS.exists():
            punto = torch.load(RUTA_DOS_VISTAS, map_location="cpu", weights_only=False)
            vistas = len(punto.get("clases_entrenadas", []))
            if vistas < MINIMO_CLASES_DOS_VISTAS:
                _dos_motivo = f"entrenado con {vistas} de {len(punto['clases'])} clases: faltan fotos de las demás"
                return None
            tamano = int(punto.get("tamano", TAMANO_ENTRADA))
            red = RedDosVistas(cantidad_clases=len(punto["clases"]), tamano=tamano)
            red.load_state_dict(punto["pesos"])
            red.eval()
            _dos = (red, list(punto["clases"]), tamano, punto.get("recorte", "ampliado"))
    return _dos


def motivo_dos_vistas_ignorado() -> str | None:
    """Por qué existe el archivo del modelo de dos vistas pero no se usa (`None` si se usa o no existe)."""
    _cargar_dos_vistas()
    return _dos_motivo


def hay_dos_vistas() -> bool:
    """Si existe un modelo entrenado con las dos cámaras a la vez (`training/entrenar_dos_vistas.py`)."""
    return _cargar_dos_vistas() is not None


def modo_dos_vistas() -> str:
    """Con qué recorte se entrenó el modelo de dos vistas: `"ampliado"` o `"volumen"`."""
    modelo = _cargar_dos_vistas()
    return modelo[3] if modelo else "ampliado"


def clases_dos_vistas() -> list[str]:
    modelo = _cargar_dos_vistas()
    return list(modelo[1]) if modelo else []


def probabilidades_dos_vistas(recortes_por_camara: dict[str, list[np.ndarray]]) -> np.ndarray:
    """Probabilidades `(n, clases)` del modelo de dos vistas. `recortes_por_camara` = `{"principal": [..n recortes..], "secundaria": [..]}`.

    Con una sola cámara la otra vista se anula (máscara 0). Todas las listas deben tener los mismos `n` recortes, en el mismo orden de casillas.
    """
    modelo = _cargar_dos_vistas()
    if modelo is None:
        raise FileNotFoundError(f"No se encontró {RUTA_DOS_VISTAS} — correr antes `python -m training.entrenar_dos_vistas`")
    red, _, tamano, _ = modelo
    cantidad = len(next(iter(recortes_por_camara.values())))
    vacio = torch.zeros(cantidad, 3, tamano, tamano)
    entradas = [vacio, vacio]
    mascara = torch.zeros(cantidad, 2)
    for camara, recortes in recortes_por_camara.items():
        ranura = RANURAS[camara]
        entradas[ranura] = torch.stack([preprocesar_recorte(r, tamano) for r in recortes])
        mascara[:, ranura] = 1.0
    with torch.no_grad():
        return torch.softmax(red(entradas[0], entradas[1], mascara), dim=1).numpy()


def invalidar_modelo() -> None:
    """Descarta el clasificador cacheado: el próximo `clasificar_pieza` recarga el checkpoint (tras un reentrenamiento)."""
    global _modelo, _clases, _dos, _dos_buscado, _dos_motivo
    _modelo = None
    _clases = None
    _dos, _dos_buscado, _dos_motivo = None, False, None


def clasificar_pieza(recorte_casilla: np.ndarray) -> str:
    """Predice qué hay en una casilla: "vacia" o una pieza (ej. "white-knight").

    Args:
        recorte_casilla: recorte BGR de la casilla, tal como lo devuelve
            `backend.servicios.vision.tablero.dividir_en_casillas`.

    Returns:
        La etiqueta de clase con mayor probabilidad.
    """
    modelo, clases = _cargar_modelo()
    entrada = preprocesar_recorte(recorte_casilla, _tamano).unsqueeze(0)  # agrega dimensión de lote
    with torch.no_grad():
        indice = modelo(entrada).argmax(dim=1).item()
    return clases[indice]


def clases_del_modelo() -> list[str]:
    """Las clases del modelo cargado, en el orden de las columnas de `probabilidades`."""
    _cargar_modelo()
    return list(_clases)


def probabilidades(recortes: list[np.ndarray]) -> np.ndarray:
    """Probabilidad de cada clase para cada recorte: matriz `(n, clases)` (una sola pasada por la red)."""
    modelo, _ = _cargar_modelo()
    entradas = torch.stack([preprocesar_recorte(r, _tamano) for r in recortes])
    with torch.no_grad():
        return torch.softmax(modelo(entradas), dim=1).numpy()


def mejores_clases(probs: np.ndarray, cantidad: int = 3, clases: list[str] | None = None) -> list[list[tuple[str, float]]]:
    """Las `cantidad` clases más probables de cada fila de `probs`, como `(clase, probabilidad)`. `clases`: nombres de las columnas (por defecto las del modelo de una vista)."""
    clases = clases or clases_del_modelo()
    orden = np.argsort(probs, axis=1)[:, ::-1][:, :cantidad]
    return [[(clases[i], float(fila[i])) for i in indices] for fila, indices in zip(probs, orden)]


def clasificar_con_confianza(recortes: list[np.ndarray], cantidad: int = 3) -> list[list[tuple[str, float]]]:
    """Para cada recorte, las `cantidad` clases más probables con su probabilidad (una sola pasada por la red)."""
    if not recortes:
        return []
    return mejores_clases(probabilidades(recortes), cantidad)
