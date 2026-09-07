# Brazo Robótico con Inteligencia Artificial para el Aprendizaje del Ajedrez

Sistema que reconoce un tablero de ajedrez real mediante visión por computadora, calcula la
jugada con el motor Stockfish, y la explica mediante un modelo de aprendizaje propio. La ejecución
física con un brazo robótico queda para una fase posterior; por ahora todo el flujo es virtual y
el brazo se simula con PyBullet.

Proyecto académico — Ingeniería de Software II, UAGRM (2/2026).
Equipo: Suárez Burgos Hebert, Arze Kao Luis Ángel.

## Stack

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12+ |
| Visión por computadora | OpenCV |
| Motor de ajedrez | Stockfish + `python-chess` |
| Modelo de aprendizaje | PyTorch, entrenado en Google Colab |
| Simulación del brazo | PyBullet |
| Backend / API | FastAPI |
| Frontend | React + Vite |

## Estructura

Arquitectura en capas (MVC) — ver `PLAN_IMPLEMENTACION_COMPLETO.md`, secciones 3 y 4, para el
detalle de la arquitectura y los patrones de diseño aplicados (Strategy, Factory, Repository).

```
backend/
├── rutas/              # capa de Rutas (Controlador) — endpoints HTTP
├── servicios/           # capa de Servicios (lógica real)
│   ├── motor/             # Stockfish + python-chess
│   ├── partida/            # orquesta partidas jugables (usa repositorios/ y estrategias/)
│   ├── estrategias/         # patrón Strategy + Factory: quién decide la jugada
│   ├── vision/                # reconocimiento de tablero y piezas
│   └── simulacion/             # integración con PyBullet
├── repositorios/          # patrón Repository: acceso a datos de partidas
├── esquemas/               # capa de Esquemas (Pydantic) — DTOs de entrada/salida
├── modelos/                 # capa de Modelos de datos — entidades (Partida)
└── main.py                    # arma la app y monta el build del frontend
training/              # pipeline de datos, entrenamiento del clasificador de piezas y notebook
frontend/                # proyecto React (Vite) — tablero interactivo + consola del motor
docs/                     # historias de usuario, C4, plan por sprint
```

## Setup

Requiere el binario de Stockfish instalado (por ejemplo `brew install stockfish` en macOS,
disponible en el `PATH` como `stockfish`) y [conda/miniforge](https://github.com/conda-forge/miniforge)
para el entorno de Python.

Se usa conda en vez de un venv plano porque `pybullet` no siempre tiene wheel instalable con `pip`
en macOS (compila desde código y puede fallar según la versión de Xcode/SDK) — conda-forge sí trae
binarios precompilados.

```bash
conda env create -f environment.yml
conda activate ajedrez
```

Si `environment.yml` ya existe y solo cambiaron dependencias de `requirements.txt`:

```bash
conda activate ajedrez
pip install -r requirements.txt
```

## Frontend (React)

Requiere Node.js 20+.

```bash
cd frontend
npm install
npm run dev       # desarrollo, en http://localhost:5173 (proxea la API a :8000)
npm run build     # genera frontend/dist — el backend lo sirve automáticamente en "/"
```

Con el backend corriendo (`uvicorn backend.main:app`) y `frontend/dist` construido, todo el
sistema queda disponible en un solo puerto: `http://127.0.0.1:8000`.

## Tests

```bash
python -m pytest
```

El frontend todavía no tiene tests automatizados (no se armó el setup de Vitest) — se prueba
manualmente contra el backend real.

## Documentación

- [`docs/plan_sprints.md`](docs/plan_sprints.md) — backlog por sprint con seguimiento de tareas.
