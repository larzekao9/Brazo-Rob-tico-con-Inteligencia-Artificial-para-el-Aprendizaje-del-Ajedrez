# Brazo Robótico con Inteligencia Artificial para el Aprendizaje del Ajedrez

Sistema que reconoce un tablero de ajedrez real mediante visión por computadora, calcula la
jugada con el motor Stockfish, y la explica mediante un modelo de aprendizaje propio. La ejecución
física con un brazo robótico queda para una fase posterior; por ahora todo el flujo es virtual y
el brazo se simula con PyBullet.

Proyecto académico — Ingeniería de Software II, UAGRM (2/2026).
Equipo: Suárez Burgos Hebert, Arce Kao Luis Ángel.

## Stack

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12+ |
| Visión por computadora | OpenCV |
| Motor de ajedrez | Stockfish + `python-chess` |
| Modelo de aprendizaje | PyTorch, entrenado en Google Colab |
| Simulación del brazo | PyBullet |
| Backend / API | FastAPI |

## Estructura

```
backend/
├── engine/          # wrapper de Stockfish + python-chess
├── vision/          # reconocimiento de tablero y piezas (próximamente)
├── learning/        # inferencia del modelo entrenado (próximamente)
├── simulation/       # integración con PyBullet (próximamente)
└── models/           # entidades: Partida, Jugada, Sesión, Progreso (próximamente)
training/             # pipeline de datos y notebook de entrenamiento (próximamente)
frontend/              # aplicación de control / visualización (próximamente)
docs/                  # historias de usuario, C4, plan por sprint
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

## Tests

```bash
python -m pytest
```

## Documentación

- [`docs/plan_sprints.md`](docs/plan_sprints.md) — backlog por sprint con seguimiento de tareas.
