# Plan: Backend Razonamiento Neuronal — Implementación por Fases

**Objetivo**: Conectar datos reales al panel "Razonamiento Neuronal" (endpoint `/aprendizaje/inferencia`, `/aprendizaje/estado-modelo`).

---

## Agentes y responsabilidades

| Agente | Dominio | Qué entrega |
|--------|---------|-------------|
| `modelo-entrenamiento` | Pipeline ML / inferencia | `inferencia.py` (funciones reales), `test_inferencia.py` |
| `backend-fastapi` | API / esquemas / wiring | `aprendizaje_esquema.py`, `ruta_aprendizaje.py`, registro en `main.py` |
| `qa-reviewer` (al final) | Verificación | pytest + pruebas manuales endpoints |

---

## Fases (ejecutables en paralelo donde no hay dependencia)

### ✅ FASE 1 — Inferencia real (agente: `modelo-entrenamiento`)
**Archivos**: `backend/servicios/aprendizaje/inferencia.py`, `backend/servicios/aprendizaje/test_inferencia.py`

**Entregables**:
- `predecir_top_jugadas(fen, top_n=3, ruta_checkpoint) -> list[tuple[str, float]]`
  - Softmax solo sobre jugadas legales (mismo filtro que `predecir_jugada`)
  - Devuelve SAN + probabilidad real
- `calcular_saliencia(fen, ruta_checkpoint) -> list[float]` (64 valores [0,1])
  - Gradiente de entrada real: `requires_grad_(True)` → forward → `backward()` sobre score jugada elegida
  - `input.grad.abs().sum(dim=1)` por casilla → normalizar 0-1
- `estado_modelo(ruta_checkpoint) -> dict`
  - Parse versión/fecha del nombre (`modelo_jugadas_v(\d+)_(\d{4}-\d{2}-\d{2})\.pt`)
  - `num_clases` del checkpoint
  - Dispositivo real: `torch.cuda.get_device_name(0)` si CUDA, si no `"cpu"`
- Latencia real con `time.perf_counter()` alrededor de inferencia
- **Manejo checkpoint ausente**: propagar `FileNotFoundError` (no capturar aquí)

**Tests** (extender `test_inferencia.py` existente):
- Shape `calcular_saliencia` = 64 valores en [0,1]
- `predecir_top_jugadas` probabilidades suman ~1
- `estado_modelo` parsea nombre archivo correctamente
- Mismo patrón "skip si no hay torch" que `test_modelo_jugadas.py`

---

### ✅ FASE 2 — Esquemas Pydantic (agente: `backend-fastapi`)
**Archivo**: `backend/esquemas/aprendizaje_esquema.py` (nuevo)

```python
class CandidataModelo(BaseModel):
    jugada: str
    probabilidad: float

class ComparacionStockfish(BaseModel):
    jugada_motor: str
    evaluacion_cp: int
    diferencia_cp: int

class InferenciaModeloRequest(BaseModel):
    fen: str

class InferenciaModeloResponse(BaseModel):
    jugada_elegida: str
    candidatas: list[CandidataModelo]
    latencia_ms: float
    comparacion_stockfish: ComparacionStockfish
    saliencia: list[float]  # 64 floats

class EstadoModeloResponse(BaseModel):
    version: int
    fecha_entrenamiento: str
    num_clases: int
    dispositivo: str
    disponible: bool
```

---

### ✅ FASE 3 — Rutas HTTP (agente: `backend-fastapi`)
**Archivo**: `backend/rutas/ruta_aprendizaje.py` (nuevo)

```python
router = APIRouter(prefix="/aprendizaje", tags=["aprendizaje"])

@router.get("/estado-modelo")
def estado_modelo_endpoint():
    try:
        data = estado_modelo()
        return EstadoModeloResponse(**data, disponible=True)
    except FileNotFoundError:
        return EstadoModeloResponse(
            version=0, fecha_entrenamiento="", num_clases=0,
            dispositivo="none", disponible=False
        )

@router.post("/inferencia")
def inferencia_endpoint(req: InferenciaModeloRequest):
    try:
        candidatas = predecir_top_jugadas(req.fen, top_n=3)
        saliencia = calcular_saliencia(req.fen)
        # Stockfish SOLO como comparación (regla 1 CLAUDE.md)
        stockfish = analizar_posicion(req.fen, nivel=20)
        # latencia real ya viene medida en inferencia.py o se mide aquí
        return InferenciaModeloResponse(
            jugada_elegida=candidatas[0][0],
            candidatas=[CandidataModelo(jugada=j, probabilidad=p) for j,p in candidatas],
            latencia_ms=...,  # medir aquí o traer de inferencia.py
            comparacion_stockfish=ComparacionStockfish(...),
            saliencia=saliencia
        )
    except FileNotFoundError:
        raise HTTPException(503, "Modelo no disponible en este entorno")
```

---

### ✅ FASE 4 — Wiring en main.py (agente: `backend-fastapi`)
**Archivo**: `backend/main.py`

```python
from backend.rutas.ruta_aprendizaje import router as aprendizaje_router
app.include_router(aprendizaje_router)
```

---

### ✅ FASE 5 — Verificación (agente: `qa-reviewer`)
- `pytest backend/servicios/aprendizaje/test_inferencia.py -v`
- `pytest backend/ -v` (suite general)
- Levantar backend: `uvicorn backend.main:app --reload`
- Probar:
  - `GET /aprendizaje/estado-modelo` → 200 con `disponible=true/false`
  - `POST /aprendizaje/inferencia` con FEN real → 200 con datos completos
  - Sin checkpoint local → 503 en `/inferencia`, 200 con `disponible=false` en `/estado-modelo`

---

## Dependencias entre fases

```
FASE 1 (modelo-entrenamiento) ──────┐
                                    ├──► FASE 2 (backend-fastapi) ──► FASE 3 (backend-fastapi) ──► FASE 4 (backend-fastapi) ──► FASE 5 (qa-reviewer)
FASE 2 (backend-fastapi) ───────────┘
```

**Paralelismo**: FASE 1 y FASE 2 son **independientes** → se pueden ejecutar en paralelo con dos subagentes.

---

## Checklist de cierre (regla CLAUDE.md)

- [ ] Tests pasan (`pytest backend/servicios/aprendizaje/test_inferencia.py`)
- [ ] Suite general pasa
- [ ] Endpoints responden correctamente (con y sin checkpoint)
- [ ] Grafo de conocimiento actualizado (`code-review-graph` / `graphify`)
- [ ] Commit + push **sin menciones a IA** en mensajes