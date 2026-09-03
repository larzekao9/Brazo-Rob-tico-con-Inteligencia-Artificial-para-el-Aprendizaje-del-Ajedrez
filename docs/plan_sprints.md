# Plan de implementación por sprint

Basado en el plan de 3 semanas de `PLAN_IMPLEMENTACION.md` (sección 5). Cada sprint dura 1 semana.
No cambia el alcance ni el orden ya definidos ahí — solo lo reorganiza en formato backlog +
Definition of Done para seguimiento semana a semana.

---

## Sprint 1 — Fundamentos y arranque en paralelo

**Objetivo del sprint:** tener el motor de ajedrez respondiendo jugadas de forma aislada, y el
pipeline de datos corriendo de punta a punta con un subconjunto chico.

### Backlog conjunto (día 1-2)
- [x] Estructura de repositorio (`backend/`, `training/`, `frontend/`, `docs/`).
- [x] `requirements.txt` con versiones exactas.
- [ ] `docs/historias_usuario.md` — Alcance del Perfil de Proyecto reformateado como historias.
- [ ] `docs/c4/` — C4 de Contexto y Contenedores.

### Backlog Hebert — motor de ajedrez
- [x] Instalar Stockfish y probarlo desde `python-chess`.
- [x] `backend/engine/stockfish_wrapper.py`: `calcular_jugada(fen, nivel)`.
- [x] Test con posiciones conocidas (aperturas + mate en 1).

### Backlog Luis Ángel — pipeline de datos
- [ ] Descargar un mes de Lichess (mes viejo, 2013-2014, ver nota de tamaño arriba).
- [ ] `training/data_pipeline.py`:
  - `board_to_tensor(board) -> np.ndarray (8, 8, 12)` — desde la perspectiva del jugador a mover.
  - `pgn_to_samples(path, limit) -> list[(tensor, etiqueta)]` — etiqueta = `from_square * 64 + to_square`.
- [ ] Validar en Colab con 100-200 partidas: confirmar shapes y que las etiquetas coinciden con
      `move.from_square` / `move.to_square` de `python-chess`.

**Definition of Done del sprint:** `calcular_jugada(fen, nivel)` funciona y tiene tests en verde;
`data_pipeline.py` corre sobre 100-200 partidas sin errores y produce tensores con la forma esperada.

---

## Sprint 2 — Visión + entrenamiento real

**Objetivo del sprint:** reconocer un tablero desde una foto y tener una primera versión entrenada
del modelo (sin buscar precisión todavía).

### Backlog Hebert — visión
- [ ] Set de 15-20 fotos de tablero (luz y ángulo variados).
- [ ] Detección de las 64 casillas (transformación de perspectiva + grilla, OpenCV).
- [ ] Clasificación de pieza por casilla (modelo preentrenado como base, no CNN propia todavía).
- [ ] `tablero_a_fen(imagen) -> str`.

### Backlog Luis Ángel — entrenamiento
- [ ] Primera versión del modelo en Colab (arquitectura simple, pocas épocas) — validar pipeline
      end-to-end, no precisión.
- [ ] Checkpoints a Google Drive cada N épocas (la sesión de Colab puede cortarse sin avisar).
- [ ] `explicar_jugada(fen, jugada) -> str` (puede ser genérica al principio).

**Definition of Done del sprint:** una foto de tablero produce un FEN válido; existe al menos un
checkpoint entrenado y versionado en Drive, cargable para inferencia.

---

## Sprint 3 — Integración y preparación de la defensa

**Objetivo del sprint:** flujo completo funcionando end-to-end y demo lista.

### Backlog conjunto
- [ ] Integración: imagen → visión → FEN → Stockfish calcula jugada → modelo explica → resultado
      en pantalla.
- [ ] Interfaz mínima de visualización del razonamiento (imagen, jugada, explicación).
- [ ] Probar con al menos 10 posiciones distintas, documentar errores.
- [ ] Colchón de 2-3 días antes de la defensa para bugs de integración.
- [ ] Preparar 2-3 posiciones para la demo en vivo.

**Definition of Done del sprint:** demo reproducible de punta a punta con al menos 10 posiciones
probadas y documentadas; nada de esto depende del brazo físico real.

---

## Notas de seguimiento

- Marcar los checkboxes a medida que se completan las tareas — este archivo es el tablero de
  seguimiento, `PLAN_IMPLEMENTACION.md` sigue siendo la fuente de verdad del alcance y las reglas.
- Cualquier tarea que no se pueda completar en su sprint se avisa explícitamente antes de pasar al
  siguiente, no se arrastra en silencio.
