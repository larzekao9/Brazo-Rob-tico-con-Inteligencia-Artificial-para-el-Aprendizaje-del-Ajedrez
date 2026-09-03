# Plan de implementación por sprint

Basado en el plan de 3 semanas de `PLAN_IMPLEMENTACION.md` (sección 5). Cada sprint dura 1 semana.
No cambia el alcance ni las reglas ya definidas ahí — lo organiza por **área** en vez de por
persona, para poder avanzar varias áreas en paralelo dentro de cada sprint.

Áreas: **Motor** · **Visión** · **Modelo/Entrenamiento** · **Backend** · **Simulador** · **Frontend**.

---

## Sprint 1 — Fundamentos y arranque en paralelo

**Objetivo:** motor de ajedrez respondiendo jugadas de forma aislada, pipeline de datos corriendo
de punta a punta con un subconjunto chico, y un backend mínimo que ya expone el motor.

### Conjunto (día 1-2)
- [x] Estructura de repositorio (`backend/`, `training/`, `frontend/`, `docs/`).
- [x] `requirements.txt` con versiones exactas.
- [ ] `docs/historias_usuario.md` — Alcance del Perfil de Proyecto reformateado como historias.
- [ ] `docs/c4/` — C4 de Contexto y Contenedores.

### Motor (Hebert)
- [x] Instalar Stockfish y probarlo desde `python-chess`.
- [x] `backend/engine/stockfish_wrapper.py`: `calcular_jugada(fen, nivel)`.
- [x] Test con posiciones conocidas (aperturas + mate en 1).

### Modelo/Entrenamiento (Luis Ángel)
- [x] Descargar un mes de Lichess (2017-02 — más grande que lo recomendado, 1.8 GB comprimido,
      pero el pipeline lee en streaming así que no hace falta descomprimirlo entero).
- [x] `training/data_pipeline.py`:
  - `board_to_tensor(board) -> np.ndarray (8, 8, 12)` — desde la perspectiva del jugador a mover.
  - `pgn_to_samples(path, limite_partidas) -> list[(tensor, etiqueta)]` — etiqueta =
    `from_square * 64 + to_square`, también en perspectiva del jugador a mover.
- [x] Validado localmente (no en Colab todavía) con partidas sintéticas + 5 partidas reales del
      dataset descargado: shapes y etiquetas correctas. Falta correrlo en Colab con 100-200
      partidas reales antes de escalar a todo el mes.

### Backend
- [x] `backend/main.py` — FastAPI mínimo.
- [x] `POST /jugada` (`fen`, `nivel`) → llama a `calcular_jugada`, devuelve la jugada.
- [x] `backend/models/` — esquemas Pydantic de request/response (no las entidades completas
      todavía, solo lo que necesita este endpoint).
- [x] `POST /analisis` (`fen`, `nivel`) → llama a `analizar_posicion` (adelantado, no bloqueaba).

**Definition of Done:** `calcular_jugada(fen, nivel)` en verde; `data_pipeline.py` corre sobre
100-200 partidas sin errores; `POST /jugada` responde una jugada válida vía HTTP.

---

## Sprint 2 — Visión + entrenamiento real

**Objetivo:** reconocer un tablero desde una foto, primera versión entrenada del modelo (sin
buscar precisión todavía), y el simulador mostrando la jugada calculada.

### Visión (Hebert)
- [ ] Set de 15-20 fotos de tablero (luz y ángulo variados).
- [ ] Detección de las 64 casillas (transformación de perspectiva + grilla, OpenCV).
- [ ] Clasificación de pieza por casilla (modelo preentrenado como base, no CNN propia todavía).
- [ ] `tablero_a_fen(imagen) -> str`.

### Modelo/Entrenamiento (Luis Ángel)
- [ ] Primera versión del modelo en Colab (arquitectura simple, pocas épocas) — validar pipeline
      end-to-end, no precisión.
- [ ] Checkpoints a Google Drive cada N épocas.
- [ ] `explicar_jugada(fen, jugada) -> str` (puede ser genérica al principio).

### Simulador
- [x] `backend/simulation/` — escena PyBullet con un tablero 3D estático (sin brazo — el kit
      físico está fuera de alcance).
- [x] `resaltar_jugada(desde, hasta)` — marca visualmente casilla origen/destino de la jugada
      calculada. Sin cinemática inversa ni animación de brazo: es deliberadamente simple para no
      arriesgar el resto del plan. (Adelantado desde Sprint 2, no dependía de nada más.)

**Definition of Done:** una foto de tablero produce un FEN válido; existe un checkpoint entrenado
en Drive; la escena de PyBullet resalta origen/destino de una jugada dada.

---

## Sprint 3 — Integración y preparación de la defensa

**Objetivo:** flujo completo funcionando end-to-end y demo lista.

### Backend
- [ ] `POST /analizar` (imagen) → visión → FEN → `calcular_jugada` → `explicar_jugada` →
      respuesta única con jugada + explicación.
- [ ] Endpoint que dispare `resaltar_jugada` en el simulador tras cada jugada calculada.

### Frontend
- [x] Página única servida por el mismo FastAPI (Jinja2 + fetch a los endpoints) — sin proyecto
      React aparte, para no sumar infraestructura que no aporta a lo evaluado. (Adelantado; hoy
      pide FEN a mano, todavía no imagen — depende de Visión.)
- [ ] Vista de "Visualización del Razonamiento en Tiempo Real": imagen capturada, jugada elegida,
      explicación (falta conectar imagen real y `explicar_jugada`).

### Simulador
- [ ] Conectar `resaltar_jugada` al resultado real de `POST /analizar`.

### Conjunto
- [ ] Probar el flujo completo con al menos 10 posiciones distintas, documentar errores.
- [ ] Colchón de 2-3 días antes de la defensa para bugs de integración.
- [ ] Preparar 2-3 posiciones para la demo en vivo.

**Definition of Done:** demo reproducible de punta a punta (imagen → jugada → explicación →
resaltado en el simulador) con al menos 10 posiciones probadas y documentadas; nada de esto
depende del brazo físico real.

---

## Notas de seguimiento

- Marcar los checkboxes a medida que se completan las tareas — este archivo es el tablero de
  seguimiento, `PLAN_IMPLEMENTACION.md` sigue siendo la fuente de verdad del alcance y las reglas.
- Cualquier tarea que no se pueda completar en su sprint se avisa explícitamente antes de pasar al
  siguiente, no se arrastra en silencio.
- Backend, Simulador y Frontend no tienen dueño fijo asignado en `PLAN_IMPLEMENTACION.md` — se
  reparten según disponibilidad, o se ejecutan con ayuda de subagentes (ver nota abajo).
