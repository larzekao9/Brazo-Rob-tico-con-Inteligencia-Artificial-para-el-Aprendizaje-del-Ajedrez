"""Deja una imagen lista para subir como ilustración de una medalla: PNG de 512x512, fondo transparente, dibujo centrado.

    python scripts/preparar_ilustracion_medalla.py imagen.png --salida carpeta_salida
    python scripts/preparar_ilustracion_medalla.py carpeta_con_imagenes --salida carpeta_salida

Sirve para lo que generan las IA de imágenes (fotos o renders con fondo): si la imagen ya trae transparencia no la toca. Si el
fondo es verde sólido (lo ideal: pedirle a la IA un fondo #00FF00) lo quita por croma, también entre los destellos y brillos
semitransparentes, sin dejar halo verde. Con otro color de fondo toma el de los bordes y lo borra desde afuera hacia adentro, así
no se borran colores parecidos que estén dentro del objeto. Después recorta, centra y agranda el dibujo (lado mayor al 89 % del
cuadrado) para que entre en el campo del escudo de la medalla. Usa Pillow y numpy, que ya están en el proyecto.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LADO = 512
OCUPA = 456  # 89 % del cuadrado: el lado mayor del dibujo (las piezas altas y flacas, como rey o alfil, quedaban chicas con menos)
RADIO_CIRCULO = 270  # el dibujo tiene que entrar en este círculo (evita que las esquinas de un dibujo cuadrado queden fuera del escudo)
EXTENSIONES = {".png", ".jpg", ".jpeg", ".webp"}
VERDE_MINIMO = 80  # cuánto tiene que dominar el verde sobre el rojo y el azul para considerar el fondo una pantalla verde


def tiene_transparencia(imagen: Image.Image) -> bool:
    """`True` si la imagen ya trae canal alfa con píxeles transparentes en los bordes."""
    if imagen.mode != "RGBA":
        return False
    ancho, alto = imagen.size
    bordes = [(0, 0), (ancho - 1, 0), (0, alto - 1), (ancho - 1, alto - 1), (ancho // 2, 0), (ancho // 2, alto - 1)]
    return any(imagen.getpixel(p)[3] < 16 for p in bordes)


def color_pantalla_verde(imagen: Image.Image) -> tuple[float, float, float] | None:
    """Color del fondo si los bordes de la imagen son un verde de croma; `None` si el fondo es de otro color."""
    ancho, alto = imagen.size
    rgb = np.asarray(imagen.convert("RGB"), dtype=np.float32)
    bordes = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    rojo, verde, azul = np.median(bordes, axis=0)
    return (rojo, verde, azul) if verde - max(rojo, azul) >= VERDE_MINIMO else None


def quitar_pantalla_verde(imagen: Image.Image, fondo: tuple[float, float, float]) -> Image.Image:
    """Quita un fondo verde por croma: la transparencia sale de cuánto domina el verde y el color del objeto se recupera
    descontando el fondo, así los destellos y brillos semitransparentes no quedan verdosos."""
    pixeles = np.asarray(imagen.convert("RGB"), dtype=np.float32)
    verde_fondo = np.array(fondo, dtype=np.float32)
    dominio_fondo = verde_fondo[1] - max(verde_fondo[0], verde_fondo[2])
    dominio = pixeles[..., 1] - np.maximum(pixeles[..., 0], pixeles[..., 2])
    alfa = np.clip(1 - dominio / dominio_fondo, 0, 1)
    alfa = np.where(alfa < 0.06, 0, np.where(alfa > 0.94, 1, alfa))
    frente = np.clip((pixeles - (1 - alfa)[..., None] * verde_fondo) / np.maximum(alfa, 1e-3)[..., None], 0, 255)
    tope = np.maximum(frente[..., 0], frente[..., 2]) * np.where(dominio > 6, 0.88, 1.0)  # sin tinte verde en lo que tocó el fondo
    frente[..., 1] = np.minimum(frente[..., 1], tope)
    return Image.fromarray(np.dstack([entibiar_verdes(frente.astype(np.uint8)), alfa * 255]).astype(np.uint8), "RGBA")


def entibiar_verdes(rgb: np.ndarray) -> np.ndarray:
    """Lleva hacia el dorado los amarillos verdosos (el rebote de la luz verde del fondo en los brillos). Los verdes puros no se tocan."""
    hsv = np.asarray(Image.fromarray(rgb, "RGB").convert("HSV")).astype(np.float32)
    grados = hsv[..., 0] * 360 / 255
    verdoso = (grados > 52) & (grados < 100) & (hsv[..., 1] > 40)
    hsv[..., 0] = np.where(verdoso, (42 + (grados - 52) * 0.08) * 255 / 360, hsv[..., 0])
    return np.asarray(Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB"))


def quitar_fondo(imagen: Image.Image, tolerancia: int, suavizado: float) -> Image.Image:
    """Borra el fondo conectado a los bordes (inundación desde los bordes con `tolerancia`) y suaviza el contorno."""
    rgba = imagen.convert("RGBA")
    ancho, alto = rgba.size
    semillas = [(0, 0), (ancho - 1, 0), (0, alto - 1), (ancho - 1, alto - 1)]
    semillas += [(ancho // 2, 0), (ancho // 2, alto - 1), (0, alto // 2), (ancho - 1, alto // 2)]
    for punto in semillas:
        if rgba.getpixel(punto)[3] > 0:
            ImageDraw.floodfill(rgba, punto, (0, 0, 0, 0), thresh=tolerancia)
    alfa = rgba.getchannel("A")
    alfa = alfa.filter(ImageFilter.MinFilter(3))  # come el borde de color del fondo
    if suavizado > 0:
        alfa = alfa.filter(ImageFilter.GaussianBlur(suavizado))
    rgba.putalpha(alfa)
    return rgba


def encuadrar(imagen: Image.Image) -> Image.Image:
    """Escala el dibujo y lo centra en un cuadrado de 512 px. El tamaño se mide con la parte sólida: las chispas y los brillos
    tenues lejanos no cuentan (si se salen del cuadrado, se cortan)."""
    alfa = imagen.getchannel("A")
    caja = alfa.point(lambda a: 255 if a > 100 else 0).getbbox() or alfa.point(lambda a: 255 if a > 8 else 0).getbbox()
    if caja is None:
        raise ValueError("la imagen quedó vacía (no se encontró ningún dibujo)")
    ancho, alto = caja[2] - caja[0], caja[3] - caja[1]
    escala = min(OCUPA / max(ancho, alto), 2 * RADIO_CIRCULO / math.hypot(ancho, alto))
    escalada = imagen.resize((max(1, round(imagen.width * escala)), max(1, round(imagen.height * escala))), Image.LANCZOS)
    centro_x, centro_y = (caja[0] + caja[2]) / 2 * escala, (caja[1] + caja[3]) / 2 * escala
    lienzo = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    lienzo.paste(escalada, (round(LADO / 2 - centro_x), round(LADO / 2 - centro_y)), escalada)
    return lienzo


def preparar(origen: Path, destino: Path, tolerancia: int = 70, suavizado: float = 0.8, croma: bool = True) -> list[str]:
    """Procesa una imagen. Devuelve los avisos (lista vacía si todo parece bien).

    Con `croma=False` un fondo verde se quita igual que cualquier otro color (desde los bordes hacia adentro): sirve cuando
    el objeto tiene partes verdes (una cinta, un laurel) que el croma borraría; solo se pierde la mejor limpieza de los
    destellos semitransparentes.
    """
    avisos = []
    imagen = Image.open(origen)
    imagen = imagen.convert("RGBA")
    if not tiene_transparencia(imagen):
        fondo_verde = color_pantalla_verde(imagen) if croma else None
        imagen = quitar_pantalla_verde(imagen, fondo_verde) if fondo_verde else quitar_fondo(imagen, tolerancia, suavizado)
        cubierto = sum(imagen.getchannel("A").histogram()[9:]) / (imagen.width * imagen.height)
        if cubierto > 0.97:
            avisos.append("no se pudo quitar el fondo (casi toda la imagen quedó): probá con --tolerancia más alta o un fondo verde sólido")
        elif cubierto < 0.04:
            avisos.append("se borró casi todo: probá con --tolerancia más baja")
    destino.parent.mkdir(parents=True, exist_ok=True)
    encuadrar(imagen).save(destino, "PNG", optimize=True)
    if destino.stat().st_size > 2 * 1024 * 1024:
        avisos.append("pesa más de 2 MB: el sistema la va a rechazar")
    return avisos


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrada", help="una imagen o una carpeta con imágenes (png, jpg, webp)")
    p.add_argument("--salida", required=True, help="carpeta donde se guardan los PNG listos (mismo nombre que el original)")
    p.add_argument("--tolerancia", type=int, default=70, help="cuánto puede variar el color del fondo (por defecto 70; subir si queda halo)")
    p.add_argument("--suavizado", type=float, default=0.8, help="suavizado del contorno en píxeles (por defecto 0,8)")
    p.add_argument(
        "--sin-croma",
        action="store_true",
        help="no usar el croma verde: quita el fondo desde los bordes (para figuritas que llevan partes verdes, como una cinta o un laurel)",
    )
    argumentos = p.parse_args()

    entrada = Path(argumentos.entrada)
    archivos = sorted(f for f in entrada.iterdir() if f.suffix.lower() in EXTENSIONES) if entrada.is_dir() else [entrada]
    if not archivos:
        print("No encontré imágenes para procesar.")
        return 1
    problemas = 0
    for archivo in archivos:
        destino = Path(argumentos.salida) / f"{archivo.stem}.png"
        try:
            avisos = preparar(archivo, destino, argumentos.tolerancia, argumentos.suavizado, croma=not argumentos.sin_croma)
        except (OSError, ValueError) as error:
            print(f"  ✗ {archivo.name}: {error}")
            problemas += 1
            continue
        print(f"  {'!' if avisos else 'ok'} {archivo.name} -> {destino.name}" + "".join(f"\n      aviso: {a}" for a in avisos))
        problemas += bool(avisos)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
