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

Requiere Python 3.12+ y el binario de Stockfish instalado (por ejemplo `brew install stockfish`
en macOS, disponible en el `PATH` como `stockfish`).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Tests

```bash
python -m pytest
```

## Documentación

- [`docs/plan_sprints.md`](docs/plan_sprints.md) — backlog por sprint con seguimiento de tareas.
