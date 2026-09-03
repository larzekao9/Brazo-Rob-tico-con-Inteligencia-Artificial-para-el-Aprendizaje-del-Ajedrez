"""Router del frontend: sirve la página única de visualización del razonamiento."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

FRONTEND_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"

POSICION_INICIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
NIVEL_DEFAULT = 20
NIVEL_MIN = 0
NIVEL_MAX = 20

templates = Jinja2Templates(directory=TEMPLATES_DIR)
static_files = StaticFiles(directory=STATIC_DIR)

router = APIRouter()


@router.get("/")
def index(request: Request):
    """Renderiza la página única con el tablero, la jugada y la explicación."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "fen_inicial": POSICION_INICIAL_FEN,
            "nivel_default": NIVEL_DEFAULT,
            "nivel_min": NIVEL_MIN,
            "nivel_max": NIVEL_MAX,
        },
    )
