"""Genera las ilustraciones de las 13 medallas de fábrica: PNG de 512x512 con fondo transparente, listos para subir.

    python scripts/generar_ilustraciones_medallas.py --salida C:/Users/USUARIO/Downloads/medallas_ilustraciones

Cada dibujo es un SVG escrito acá (un solo objeto centrado dentro de un círculo del 85 % del cuadrado, sin marco, sin escudo y sin
texto: el escudo, su color y su brillo los pone el sistema según el nivel). Los PNG se obtienen con Chrome sin ventana
(`--headless`, fondo transparente); también se escribe una hoja de contacto (`hoja_de_contacto.png`) con cada dibujo dentro del
escudo de su nivel, para revisar cómo se va a ver. Los archivos se llaman como el código de la medalla (`primer_peon.png`), que es lo
que el sistema espera.
"""
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

TINTA = "#2a1d3a"
CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


# --------------------------------------------------------------------------------------------------- piezas y formas
def degradado(id_: str, *paradas: str, horizontal: bool = False) -> str:
    """`<linearGradient>` con las paradas equidistantes (de arriba hacia abajo, o de izquierda a derecha)."""
    ejes = 'x1="0" y1="0" x2="1" y2="0"' if horizontal else 'x1="0" y1="0" x2="0" y2="1"'
    n = len(paradas) - 1
    cuerpo = "".join(f'<stop offset="{i / n:.2f}" stop-color="{c}"/>' for i, c in enumerate(paradas))
    return f'<linearGradient id="{id_}" {ejes}>{cuerpo}</linearGradient>'


DEFS_COMUNES = "".join(
    [
        degradado("marfil", "#ffffff", "#f6e9c8", "#d9c08c"),
        degradado("oro", "#fff4b0", "#ffd84a", "#e59a12"),
        degradado("rojo", "#ff8a80", "#e53946", "#a8202d"),
        degradado("acero", "#f1f5fb", "#a9b7cc", "#6f7f98"),
        degradado("piedra", "#e3e8f2", "#9aa7bf", "#5f6d88"),
        degradado("azul", "#8fd3ff", "#2f8cff", "#1747b8"),
        degradado("verde", "#9cf0a0", "#2fc254", "#17803a"),
        degradado("fuego", "#ffe36b", "#ff9a1f", "#e8341c"),
        degradado("cristal", "#fffbd0", "#ffe566", "#ffb21f"),
        degradado("robot", "#bff4ff", "#56c5e0", "#2a7f9e"),
        degradado("cuero", "#c98a52", "#8a5430"),
        degradado("crin", "#8a5a3a", "#4a2c1a"),
        degradado("papel", "#ffffff", "#e5ecf7"),
    ]
)


def estrella(cx: float, cy: float, radio: float, relleno: str = "url(#oro)", puntas: int = 5) -> str:
    puntos = []
    for i in range(puntas * 2):
        r = radio if i % 2 == 0 else radio * 0.45
        angulo = -math.pi / 2 + i * math.pi / puntas
        puntos.append(f"{cx + r * math.cos(angulo):.1f},{cy + r * math.sin(angulo):.1f}")
    return f'<polygon points="{" ".join(puntos)}" fill="{relleno}" stroke="{TINTA}" stroke-width="8" stroke-linejoin="round"/>'


def contorno(cuerpo: str, relleno: str = "none", grosor: int = 9) -> str:
    return f'<g fill="{relleno}" stroke="{TINTA}" stroke-width="{grosor}" stroke-linejoin="round" stroke-linecap="round">{cuerpo}</g>'


def base_pieza(relleno: str, y: int = 336) -> str:
    """Dos zócalos redondeados donde se apoyan las piezas."""
    return contorno(
        f'<rect x="168" y="{y}" width="176" height="32" rx="16"/><rect x="156" y="{y + 26}" width="200" height="28" rx="14"/>',
        relleno,
    )


def peon(relleno: str = "url(#marfil)", dy: int = 0) -> str:
    cuerpo = (
        contorno('<path d="M222 214 C228 262 214 300 192 338 L320 338 C298 300 284 262 290 214 Z"/>', relleno)
        + contorno('<rect x="204" y="196" width="104" height="26" rx="13"/>', relleno)
        + contorno('<circle cx="256" cy="146" r="54"/>', relleno)
        + base_pieza(relleno)
        + '<ellipse cx="238" cy="128" rx="14" ry="22" fill="#fff" opacity=".75" transform="rotate(22 238 128)"/>'
    )
    return f'<g transform="translate(0 {dy})">{cuerpo}</g>'


def torre(relleno: str = "url(#piedra)", dy: int = 0) -> str:
    cuerpo = (
        contorno('<path d="M208 206 L198 334 H314 L304 206 Z"/>', relleno)
        + contorno(
            '<path d="M182 104 H224 V134 H236 V104 H276 V134 H288 V104 H330 V174 Q330 190 314 190 H198 Q182 190 182 174 Z"/>',
            relleno,
        )
        + contorno('<rect x="194" y="186" width="124" height="24" rx="12"/>', relleno)
        + base_pieza(relleno)
        + '<rect x="196" y="116" width="14" height="46" rx="7" fill="#fff" opacity=".6"/>'
    )
    return f'<g transform="translate(0 {dy})">{cuerpo}</g>'


def caballo(relleno: str = "url(#marfil)", dy: int = 0) -> str:
    cuerpo = (
        contorno(
            '<path d="M178 340 C172 308 178 282 198 262 C176 262 150 250 132 232 C124 222 128 210 140 200 L188 156 L194 100 '
            'L222 128 C250 108 304 112 332 152 C362 194 366 282 352 340 Z"/>',
            relleno,
        )
        + '<path d="M232 126 C284 112 334 142 348 214 C354 262 352 306 348 340 L324 340 C332 270 322 194 280 154 C262 140 244 138 232 136 Z" '
        'fill="url(#crin)" stroke="' + TINTA + '" stroke-width="8" stroke-linejoin="round"/>'
        + f'<circle cx="208" cy="178" r="10" fill="{TINTA}"/><circle cx="211" cy="175" r="3.5" fill="#fff"/>'
        + f'<circle cx="144" cy="214" r="6" fill="{TINTA}"/>'
        + f'<path d="M156 244 Q176 252 196 246" fill="none" stroke="{TINTA}" stroke-width="7" stroke-linecap="round"/>'
        + base_pieza(relleno, 340)
    )
    return f'<g transform="translate(0 {dy})">{cuerpo}</g>'


def corona(cx: float, cy: float, escala: float, rotacion: float = 0) -> str:
    joyas = "".join(
        f'<circle cx="{x}" cy="{y}" r="11" fill="{c}" stroke="{TINTA}" stroke-width="5"/>'
        for x, y, c in ((-86, -92, "#ff5d73"), (0, -118, "#5dd0ff"), (86, -92, "#7dff9a"))
    )
    cuerpo = (
        contorno('<path d="M-100 40 L-112 -82 L-52 -32 L0 -108 L52 -32 L112 -82 L100 40 Z"/>', "url(#oro)")
        + contorno('<rect x="-104" y="26" width="208" height="38" rx="14"/>', "url(#oro)")
        + joyas
        + '<path d="M-70 0 L-62 -20" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".7"/>'
    )
    return f'<g transform="translate({cx} {cy}) rotate({rotacion}) scale({escala})">{cuerpo}</g>'


def rayo(relleno: str = "url(#oro)") -> str:
    return contorno('<path d="M298 64 L168 274 L246 274 L212 448 L356 216 L272 216 Z"/>', relleno, 10)


def engranaje(cx: float, cy: float, dientes: int = 8, r_ext: float = 150, r_int: float = 118) -> str:
    puntos = []
    ancho = math.pi / dientes
    for i in range(dientes):
        a = i * 2 * ancho
        for ang, r in ((a - ancho * 0.55, r_int), (a - ancho * 0.28, r_ext), (a + ancho * 0.28, r_ext), (a + ancho * 0.55, r_int)):
            puntos.append(f"{cx + r * math.cos(ang):.1f},{cy + r * math.sin(ang):.1f}")
    return contorno(f'<polygon points="{" ".join(puntos)}"/>', "url(#acero)") + contorno(
        f'<circle cx="{cx}" cy="{cy}" r="46"/>', "#3b3355"
    )


# ----------------------------------------------------------------------------------------------- las 13 ilustraciones
def ilustraciones() -> dict[str, tuple[str, str]]:
    """`codigo -> (nivel de la medalla, contenido del SVG)`."""
    d = {}

    d["primer_peon"] = ("bronce", peon(dy=34) + estrella(256, 78, 56))

    d["peon_valiente"] = (
        "bronce",
        contorno('<path d="M222 206 C176 214 128 262 112 360 C168 330 210 330 250 340 Z"/>', "url(#rojo)")
        + peon(dy=20)
        + contorno('<path d="M396 120 L418 120 L418 292 L407 312 L396 292 Z"/>', "url(#acero)")
        + contorno('<rect x="374" y="288" width="66" height="18" rx="9"/>', "url(#oro)")
        + contorno('<rect x="398" y="304" width="18" height="54" rx="9"/>', "url(#cuero)"),
    )

    d["salto_de_caballo"] = (
        "bronce",
        f'<path d="M92 430 L92 330 L168 330" fill="none" stroke="{TINTA}" stroke-width="34" stroke-linecap="round" stroke-linejoin="round" '
        f'stroke-dasharray="1 48"/>'
        f'<path d="M92 430 L92 330 L168 330" fill="none" stroke="#35d0ff" stroke-width="20" stroke-linecap="round" stroke-linejoin="round" '
        f'stroke-dasharray="1 48"/>'
        + caballo(dy=-14)
        + estrella(402, 112, 34)
        + estrella(114, 120, 24, "url(#azul)"),
    )

    rayos_bombilla = "".join(
        f'<line x1="{256 + 124 * math.cos(math.radians(a)):.1f}" y1="{214 + 124 * math.sin(math.radians(a)):.1f}" '
        f'x2="{256 + 168 * math.cos(math.radians(a)):.1f}" y2="{214 + 168 * math.sin(math.radians(a)):.1f}" '
        f'stroke="#ffcf33" stroke-width="16" stroke-linecap="round"/>'
        for a in (180, 210, 240, 270, 300, 330, 0)
    )
    d["mente_revelada"] = (
        "bronce",
        rayos_bombilla
        + contorno('<circle cx="256" cy="214" r="104"/>', "url(#cristal)")
        + contorno('<path d="M212 300 Q224 330 224 350 H288 Q288 330 300 300 Z"/>', "url(#cristal)")
        + contorno('<rect x="220" y="346" width="72" height="26" rx="10"/>', "url(#acero)")
        + contorno('<rect x="232" y="370" width="48" height="24" rx="12"/>', "url(#acero)")
        + estrella(256, 206, 44, "url(#fuego)")
        + '<ellipse cx="214" cy="168" rx="14" ry="26" fill="#fff" opacity=".7" transform="rotate(30 214 168)"/>',
    )

    d["torre_incansable"] = (
        "plata",
        torre(dy=26)
        + f'<g transform="translate(178 -2) scale(.86)">{rayo()}</g>'
        + estrella(112, 150, 28, "url(#azul)")
        + estrella(120, 392, 20, "url(#oro)"),
    )

    d["ojo_de_alfil"] = (
        "plata",
        contorno('<path d="M64 256 C126 156 386 156 448 256 C386 356 126 356 64 256 Z"/>', "url(#papel)")
        + contorno('<circle cx="256" cy="256" r="88"/>', "#1c2f6b")
        + '<circle cx="256" cy="256" r="70" fill="url(#azul)" opacity=".55"/>'
        + contorno(
            '<circle cx="256" cy="196" r="12"/><path d="M256 206 C292 218 304 252 292 284 L220 284 C208 252 220 218 256 206 Z"/>'
            '<rect x="206" y="280" width="100" height="18" rx="9"/><rect x="196" y="296" width="120" height="18" rx="9"/>',
            "url(#marfil)",
            7,
        )
        + f'<path d="M244 222 L278 258" stroke="{TINTA}" stroke-width="9" stroke-linecap="round"/>'
        + '<circle cx="214" cy="222" r="15" fill="#fff" opacity=".95"/>',
    )

    d["peon_coronado"] = ("plata", peon(dy=44) + corona(258, 98, 0.62, -10))

    marcas = "".join(
        f'<path d="M{x} 292 L{x + 24} 316 L{x + 62} 266" fill="none" stroke="{TINTA}" stroke-width="30" stroke-linecap="round" '
        f'stroke-linejoin="round"/><path d="M{x} 292 L{x + 24} 316 L{x + 62} 266" fill="none" stroke="url(#verde)" stroke-width="18" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        for x in (126, 220, 314)
    )
    d["constancia_de_roque"] = (
        "plata",
        contorno('<rect x="106" y="124" width="300" height="288" rx="38"/>', "url(#papel)")
        + contorno('<path d="M106 162 Q106 124 144 124 H368 Q406 124 406 162 V206 H106 Z"/>', "url(#rojo)")
        + contorno('<rect x="160" y="92" width="28" height="60" rx="14"/><rect x="324" y="92" width="28" height="60" rx="14"/>', "url(#acero)")
        + marcas
        + "".join(f'<circle cx="{x}" cy="372" r="11" fill="#c7d1e3"/>' for x in (150, 214, 278, 342)),
    )

    d["mate_relampago"] = (
        "oro",
        f'<g transform="translate(86 -6) scale(.9)">{rayo()}</g>'
        + contorno('<path d="M222 218 C228 268 214 304 192 340 L320 340 C298 304 284 268 290 218 Z"/>', "url(#marfil)")
        + contorno('<rect x="204" y="200" width="104" height="26" rx="13"/>', "url(#marfil)")
        + contorno('<ellipse cx="256" cy="170" rx="50" ry="44"/>', "url(#marfil)")
        + contorno('<rect x="243" y="76" width="26" height="62" rx="7"/><rect x="222" y="96" width="68" height="24" rx="7"/>', "url(#marfil)")
        + base_pieza("url(#marfil)", 338)
        + estrella(120, 150, 26, "url(#azul)"),
    )

    d["rey_de_la_racha"] = (
        "oro",
        contorno(
            '<path d="M256 136 C304 206 372 244 352 340 C342 392 300 424 256 424 C212 424 170 392 160 340 C148 280 192 256 208 206 '
            'C222 240 244 244 244 206 C244 178 250 158 256 136 Z"/>',
            "url(#fuego)",
        )
        + '<path d="M256 252 C286 290 316 316 304 366 C298 392 278 408 256 408 C234 408 214 392 208 366 C198 322 232 300 240 272 '
        'C246 290 256 292 256 252 Z" fill="#ffe97a" opacity=".95"/>'
        + corona(256, 120, 0.7),
    )

    d["domador_de_turing"] = (
        "oro",
        f'<line x1="256" y1="168" x2="256" y2="104" stroke="{TINTA}" stroke-width="26" stroke-linecap="round"/>'
        f'<line x1="256" y1="168" x2="256" y2="104" stroke="url(#acero)" stroke-width="12" stroke-linecap="round"/>'
        + contorno('<circle cx="256" cy="96" r="22"/>', "url(#rojo)")
        + contorno('<rect x="120" y="228" width="34" height="84" rx="12"/><rect x="358" y="228" width="34" height="84" rx="12"/>', "url(#acero)")
        + contorno('<rect x="146" y="164" width="220" height="200" rx="50"/>', "url(#robot)")
        + contorno('<rect x="186" y="214" width="62" height="54" rx="18"/><rect x="264" y="214" width="62" height="54" rx="18"/>', "#16314a")
        + '<circle cx="217" cy="241" r="14" fill="#7dffea"/><circle cx="295" cy="241" r="14" fill="#7dffea"/>'
        + contorno('<rect x="200" y="300" width="112" height="38" rx="12"/>', "#16314a")
        + "".join(f'<line x1="{x}" y1="304" x2="{x}" y2="334" stroke="#7dffea" stroke-width="6"/>' for x in (228, 256, 284))
        + contorno('<path d="M178 372 Q256 410 334 372" />', "none", 22)
        + f'<path d="M178 372 Q256 410 334 372" fill="none" stroke="url(#oro)" stroke-width="12" stroke-linecap="round"/>'
        + f'<path d="M334 376 C 398 372 424 340 400 296" fill="none" stroke="{TINTA}" stroke-width="18" stroke-linecap="round"/>'
        + f'<path d="M334 376 C 398 372 424 340 400 296" fill="none" stroke="url(#cuero)" stroke-width="9" stroke-linecap="round"/>'
        + contorno('<circle cx="398" cy="282" r="20"/>', "none", 9),
    )

    chispas = "".join(
        f'<line x1="{256 + 150 * math.cos(math.radians(a)):.1f}" y1="{256 + 150 * math.sin(math.radians(a)):.1f}" '
        f'x2="{256 + 196 * math.cos(math.radians(a)):.1f}" y2="{256 + 196 * math.sin(math.radians(a)):.1f}" '
        f'stroke="#ffb02e" stroke-width="14" stroke-linecap="round"/>'
        for a in (-60, -20, 20, 160, 200, 240)
    )
    d["rompe_motores"] = (
        "legendaria",
        chispas
        + engranaje(256, 256)
        + contorno('<path d="M292 112 L252 214 L290 232 L236 396"/>', "none", 22)
        + '<path d="M292 112 L252 214 L290 232 L236 396" fill="none" stroke="#ff7a1a" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
        + estrella(404, 126, 36, "url(#fuego)")
        + estrella(112, 394, 26, "url(#fuego)"),
    )

    d["aprendiz_de_turing"] = (
        "bronce",
        contorno('<path d="M120 232 Q120 188 164 188 H348 Q392 188 392 232 V332 Q392 376 348 376 H236 L150 436 L170 376 H164 Q120 376 120 332 Z"/>', "url(#papel)")
        + f'<path d="M212 262 C212 222 300 222 300 266 C300 296 256 296 256 332" fill="none" stroke="{TINTA}" stroke-width="34" stroke-linecap="round"/>'
        + '<path d="M212 262 C212 222 300 222 300 266 C300 296 256 296 256 332" fill="none" stroke="url(#azul)" stroke-width="20" stroke-linecap="round"/>'
        + f'<circle cx="256" cy="360" r="20" fill="{TINTA}"/><circle cx="256" cy="360" r="11" fill="url(#azul)"/>'
        + contorno('<path d="M256 82 L392 134 L256 186 L120 134 Z"/>', "#2b2f57")
        + contorno('<path d="M190 160 V206 Q256 232 322 206 V160"/>', "#2b2f57")
        + f'<path d="M386 138 V210" stroke="{TINTA}" stroke-width="16" stroke-linecap="round"/>'
        + '<path d="M386 138 V210" stroke="url(#oro)" stroke-width="7" stroke-linecap="round"/>'
        + contorno('<circle cx="386" cy="224" r="14"/>', "url(#oro)", 7),
    )
    return d


def ajustado(contenido: str, caja: tuple[int, int, int, int]) -> str:
    """Envuelve el dibujo para que su caja (izq, arriba, der, abajo) quede centrada y ocupe el círculo del 85 % del cuadrado."""
    izq, arriba, der, abajo = caja
    ancho, alto = max(der - izq, 1), max(abajo - arriba, 1)
    escala = min(404 / max(ancho, alto), 2 * 218 / math.hypot(ancho, alto))
    cx, cy = (izq + der) / 2, (arriba + abajo) / 2
    return f'<g transform="translate(256 256) scale({escala:.4f}) translate({-cx:.1f} {-cy:.1f})">{contenido}</g>'


def caja_visible(png: Path) -> tuple[int, int, int, int]:
    from PIL import Image  # solo para medir el dibujo ya renderizado

    alfa = Image.open(png).convert("RGBA").getchannel("A").point(lambda a: 255 if a > 8 else 0)
    return alfa.getbbox() or (0, 0, 512, 512)


def svg_de(contenido: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">'
        f"<defs>{DEFS_COMUNES}</defs>{contenido}</svg>"
    )


# ------------------------------------------------------------------------------------------------ hoja de contacto
FORMA_ESCUDO = "M50 3L90 15V55C90 78 72 92 50 98C28 92 10 78 10 55V15Z"
FORMA_CAMPO = "M50 10L83.5 20V54C83.5 74 68 86 50 91.5C32 86 16.5 74 16.5 54V20Z"
COLORES_NIVEL = {
    "bronce": ("#f0b27a", "#9a5a2b", "#7a3f1a", "#d98a4a"),
    "plata": ("#f4f6fa", "#9aa6b8", "#55627a", "#8c9ab0"),
    "oro": ("#fff0a0", "#e6a817", "#9a6a05", "#e3b030"),
    "legendaria": ("#e8d8ff", "#8a5cff", "#3a1e9a", "#6d4bd6"),
}


def figurita_html(codigo: str, nivel: str, archivo: Path) -> str:
    aro_1, aro_2, campo_1, campo_2 = COLORES_NIVEL[nivel]
    return (
        f'<div class="f"><svg viewBox="0 0 100 100" width="250" height="250">'
        f'<defs><linearGradient id="a{codigo}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{aro_1}"/><stop offset="1" stop-color="{aro_2}"/></linearGradient>'
        f'<linearGradient id="c{codigo}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{campo_2}"/><stop offset="1" stop-color="{campo_1}"/></linearGradient>'
        f'<clipPath id="k{codigo}"><path d="{FORMA_CAMPO}"/></clipPath></defs>'
        f'<path d="{FORMA_ESCUDO}" fill="url(#a{codigo})" stroke="#1d1530" stroke-width="2"/>'
        f'<path d="{FORMA_CAMPO}" fill="url(#c{codigo})"/>'
        f'<g clip-path="url(#k{codigo})"><image href="{archivo.as_uri()}" x="19" y="22" width="62" height="62"/></g>'
        f"</svg><p>{codigo}<br><small>{nivel}</small></p></div>"
    )


def convertir(chrome: str, origen: Path, destino: Path, ancho: int, alto: int, transparente: bool) -> None:
    orden = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={ancho},{alto}", f"--screenshot={destino}"]
    if transparente:
        orden.append("--default-background-color=00000000")
    orden.append(origen.as_uri())
    subprocess.run(orden, check=True, capture_output=True, timeout=90)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--salida", required=True, help="carpeta donde se guardan los PNG, los SVG y la hoja de contacto")
    argumentos = p.parse_args()
    chrome = next((c for c in CHROME if Path(c).exists()), shutil.which("chrome") or shutil.which("msedge"))
    if not chrome:
        print("No encontré Chrome ni Edge para convertir los SVG a PNG.")
        return 1
    carpeta = Path(argumentos.salida)
    (carpeta / "svg").mkdir(parents=True, exist_ok=True)

    piezas = ilustraciones()
    for codigo, (nivel, contenido) in piezas.items():
        svg, png = carpeta / "svg" / f"{codigo}.svg", carpeta / f"{codigo}.png"
        svg.write_text(svg_de(contenido), encoding="utf-8")
        convertir(chrome, svg, png, 512, 512, transparente=True)  # 1.ª pasada: medir el dibujo
        svg.write_text(svg_de(ajustado(contenido, caja_visible(png))), encoding="utf-8")
        convertir(chrome, svg, png, 512, 512, transparente=True)  # 2.ª pasada: centrado y a tamaño
        print(f"  {codigo}.png ({nivel})")

    figuritas = "".join(figurita_html(c, n, carpeta / f"{c}.png") for c, (n, _) in piezas.items())
    hoja = carpeta / "hoja_de_contacto.html"
    hoja.write_text(
        "<!doctype html><meta charset='utf-8'><style>body{margin:0;background:#12101c;color:#cfd3e4;font:13px sans-serif}"
        ".g{display:flex;flex-wrap:wrap;gap:18px;padding:22px;width:1100px}.f{width:250px;text-align:center}"
        "p{margin:6px 0 0}small{color:#8a90ad}</style><div class='g'>" + figuritas + "</div>",
        encoding="utf-8",
    )
    convertir(chrome, hoja, carpeta / "hoja_de_contacto.png", 1150, 1220, transparente=False)
    print(f"Listo: {len(piezas)} ilustraciones en {carpeta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
