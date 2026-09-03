"""API FastAPI del backend de ajedrez."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.engine.stockfish_wrapper import analizar_posicion, calcular_jugada
from backend.models.esquemas import AnalisisResponse, JugadaRequest, JugadaResponse
from frontend.router import router as frontend_router
from frontend.router import static_files

app = FastAPI(title="Ajedrez Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(frontend_router)
app.mount("/static", static_files, name="static")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Endpoint de salud del servicio."""
    return {"status": "ok"}


@app.post("/jugada", response_model=JugadaResponse)
def jugada(request: JugadaRequest) -> JugadaResponse:
    """Calcula la jugada elegida por Stockfish para la posición dada."""
    try:
        jugada_san = calcular_jugada(request.fen, nivel=request.nivel)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JugadaResponse(jugada=jugada_san)


@app.post("/analisis", response_model=AnalisisResponse)
def analisis(request: JugadaRequest) -> AnalisisResponse:
    """Analiza la posición dada y devuelve la evaluación de Stockfish."""
    try:
        resultado = analizar_posicion(request.fen, nivel=request.nivel)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return AnalisisResponse(**resultado)
