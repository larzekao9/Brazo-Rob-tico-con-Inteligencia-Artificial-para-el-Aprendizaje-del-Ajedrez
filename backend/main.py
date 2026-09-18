"""API FastAPI del backend de ajedrez."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.rutas.ruta_jugada import router as jugada_router
from backend.rutas.ruta_partida import router as partida_router
from backend.rutas.ruta_vision import router as vision_router
from backend.rutas.ruta_auth import router as auth_router

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(title="Ajedrez Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jugada_router)
app.include_router(partida_router)
app.include_router(vision_router)
app.include_router(auth_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Endpoint de salud del servicio."""
    return {"status": "ok"}


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
