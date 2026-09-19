# Brazo Robótico con Inteligencia Artificial para el Aprendizaje del Ajedrez

Plan de implementación — Ingeniería de Software II, UAGRM (2/2026)
Equipo: Suárez Burgos Hebert, Arce Kao Luis Ángel

> Este documento es el contexto del proyecto para retomar el desarrollo con ayuda de Claude Code.
> La documentación formal (PAPs y Perfil de Proyecto) ya está aprobada en su estructura; este archivo
> traduce esas decisiones en tareas concretas de programación, ordenadas para llegar con algo
> demostrable a la primera defensa (~3 semanas desde hoy).

---

## 1. Resumen del proyecto

Sistema que reconoce un tablero de ajedrez real mediante visión por computadora, calcula la jugada
con el motor Stockfish, la explica mediante un modelo de aprendizaje propio, y (en una fase
posterior, fuera del alcance de estas 3 semanas) la ejecuta físicamente con un brazo robótico.

**Para esta entrega, todo es virtual**: cámara → visión → motor/modelo → resultado en pantalla.
El brazo físico se simula con PyBullet; el hardware real (kit importado desde Perú) es una fase
posterior condicionada a su llegada — no bloquea nada de lo que sigue.

---

## 2. Stack tecnológico confirmado

| Componente | Tecnología | Notas |
|---|---|---|
| Lenguaje | Python 3.12 | Todo el sistema, un solo lenguaje |
| Visión por computadora | OpenCV | Reconocimiento de tablero y piezas |
| Motor de ajedrez | Stockfish + `python-chess` | No se reimplementa el motor, se integra |
| Modelo de aprendizaje | PyTorch (o TensorFlow) | CNN estilo Maia Chess, entrenada en Colab |
| Simulación del brazo | PyBullet | Cinemática inversa ya resuelta por la librería |
| Backend / API | FastAPI | Expone el sistema a la app de control |
| Control de versiones | GitHub | Un repo por ahora; separar en módulos, no en repos distintos |
| Entrenamiento | Google Colab (GPU gratuita T4) | Ver sección 6 |

**Reglas ya fijadas en el PAPs (no renegociar en el código):**
- Stockfish decide la jugada real; el modelo propio nunca reemplaza a Stockfish como fuente de
  la jugada — solo predice/explica al estilo humano y clasifica errores.
- El modelo se reentrena en **lotes controlados**, nunca de forma directa durante una partida.
- Fijar versiones exactas en `requirements.txt` desde el día 1 (riesgo ya identificado: R6 del PAPs).

---

## 3. Arquitectura (nivel contenedores, C4)

```
┌─────────────────┐      ┌──────────────────┐      ┌───────────────────────┐
│  Cámara / imagen │─────▶│  Módulo de Visión │─────▶│   Backend (FastAPI)   │
│   del tablero    │      │     (OpenCV)      │      │  orquesta el sistema  │
└─────────────────┘      └──────────────────┘      └───────────┬───────────┘
                                                                  │
                          ┌───────────────────────────────────────┼──────────────────┐
                          ▼                                       ▼                  ▼
                ┌──────────────────┐                 ┌─────────────────────┐  ┌─────────────┐
                │  Motor de Ajedrez │                 │  Modelo de Aprendizaje│  │  Simulación │
                │ (Stockfish/py-chess)│               │  (predicción + expl.) │  │  del Brazo  │
                └──────────────────┘                 └─────────────────────┘  │  (PyBullet) │
                                                                                └─────────────┘
                          │                                       │
                          └───────────────────┬───────────────────┘
                                               ▼
                                  ┌─────────────────────────┐
                                  │ Aplicación de Control /  │
                                  │ Visualización del        │
                                  │ Razonamiento (interfaz)  │
                                  └─────────────────────────┘
```

Este diagrama es la base para el C4 formal (ítem 3 de la pauta); ya alcanza para empezar a
programar los límites entre módulos.

---

## 4. Estructura de repositorio sugerida

```
ajedrez-robotico/
├── requirements.txt          # versiones fijadas desde el día 1
├── backend/
│   ├── main.py                # FastAPI, endpoints
│   ├── vision/                # reconocimiento de tablero y piezas
│   ├── engine/                # wrapper de Stockfish + python-chess
│   ├── learning/               # inferencia del modelo entrenado
│   ├── simulation/             # integración con PyBullet
│   └── models/                 # entidades: Partida, Jugada, Sesión, Progreso
├── training/
│   ├── colab_entrenamiento.ipynb   # notebook que corre en Colab
│   ├── data_pipeline.py            # PGN → tensores (usa python-chess)
│   └── checkpoints/                # modelos guardados (sync con Drive)
├── frontend/                  # aplicación de control / visualización
└── docs/
    ├── historias_usuario.md
    └── c4/
```

---

## 5. Plan de 3 semanas — hasta la primera defensa

### Semana 1 — Fundamentos y arranque en paralelo

**Juntos (día 1-2):**
- [ ] Crear el repositorio con la estructura de arriba.
- [ ] `requirements.txt` con versiones exactas: `python-chess`, `stockfish`, `opencv-python`,
      `pybullet`, `fastapi`, `torch` (o `tensorflow`).
- [ ] Convertir el Alcance del Perfil de Proyecto en historias de usuario (`docs/historias_usuario.md`)
      — esto ya está redactado como líneas funcionales, solo hay que reformatearlo a formato
      "Como [rol], quiero [funcionalidad], para [motivo]".
- [ ] Dibujar el C4 de Contexto y Contenedores a partir del diagrama de la sección 3.

**Hebert — motor de ajedrez primero (no visión todavía):**
- [ ] Instalar el binario de Stockfish y probarlo desde `python-chess`
      (`chess.engine.SimpleEngine.popen_uci(...)`).
- [ ] Función `calcular_jugada(fen: str, nivel: int) -> str` que reciba una posición en notación
      FEN y devuelva la jugada elegida. Esto es autocontenido: no depende de cámara ni de nada más,
      y da una victoria temprana demostrable.
- [ ] Probar con 5-10 posiciones conocidas (aperturas comunes) para verificar que responde bien.

**Luis Ángel — pipeline de datos, en paralelo:**
- [ ] Descargar un mes de partidas de `database.lichess.org` (empezar con un solo mes, no el
      dataset completo — sería demasiado grande para procesar en el tiempo disponible).
- [ ] Escribir `data_pipeline.py`: lee el PGN con `python-chess`, y para cada posición genera
      el tensor de entrada (representación del tablero) + la jugada jugada por el humano como etiqueta.
- [ ] Subir esto a un Colab y validar que el pipeline corre de punta a punta con un subconjunto
      chico (100-200 partidas) antes de escalar.

### Semana 2 — Visión + entrenamiento real

**Hebert:**
- [ ] Armar un set de 15-20 fotos de tablero en distintas condiciones (luz, ángulo) para probar
      el reconocimiento sin depender todavía de la cámara en vivo.
- [ ] Detección de las 64 casillas (transformación de perspectiva + grilla) con OpenCV.
- [ ] Clasificación de qué pieza hay en cada casilla (empezar con un clasificador simple; no hace
      falta CNN propia acá, se puede usar un modelo preentrenado de detección de objetos como base).
- [ ] Función `tablero_a_fen(imagen) -> str` — conecta visión con el motor de la semana 1.

**Luis Ángel:**
- [ ] Entrenar una primera versión del modelo en Colab (arquitectura simple, pocas épocas) —
      el objetivo esta semana es validar que el pipeline de entrenamiento funciona end-to-end,
      no lograr precisión alta todavía.
- [ ] Guardar checkpoints en Google Drive cada cierto número de épocas (Colab puede desconectar
      la sesión sin avisar — ver sección 6).
- [ ] Función `explicar_jugada(fen, jugada) -> str` que use el modelo para generar una explicación
      simple (aunque sea genérica al principio).

### Semana 3 — Integración y preparación de la defensa

**Juntos:**
- [ ] Integrar todo: cámara/imagen → visión → FEN → motor calcula jugada → modelo explica →
      resultado en pantalla. Esto cubre RP1, RP2 y parte de RP4 del PAPs.
- [ ] Interfaz mínima de "Visualización del Razonamiento en Tiempo Real" (aunque sea una página
      simple que muestre: imagen capturada, jugada elegida, explicación).
- [ ] Probar el flujo completo con al menos 10 posiciones distintas, documentar errores encontrados.
- [ ] Dejar 2-3 días de colchón antes de la defensa para bugs — casi siempre aparecen en la
      integración final.
- [ ] Preparar la demo: elegir 2-3 posiciones que se vean bien en pantalla para la presentación.

**Qué mostrar en la primera defensa:**
- Historias de usuario + C4 (ítems 2 y 3 de la pauta, ya completos).
- Demo en vivo: el sistema reconoce un tablero (de foto o cámara), Stockfish calcula la jugada,
  el modelo la explica — todo virtual, sin brazo físico.
- Avance del entrenamiento del modelo (aunque no esté con precisión final).

---

## 6. Notas sobre el uso de Google Colab

- La GPU gratuita (T4) tiene límite de horas y puede desconectar la sesión sin avisar —
  **guardar checkpoints en Google Drive cada pocas épocas**, nunca confiar solo en la sesión activa.
- Empezar con un subconjunto chico del dataset de Lichess (un mes, o incluso menos) para que
  cada ciclo de entrenamiento sea rápido de iterar. Escalar el dataset recién cuando el pipeline
  ya esté probado y funcionando.
- Si el entrenamiento se corta, retomar desde el último checkpoint guardado, no desde cero.
- Referencia de arquitectura: proyecto Maia Chess (McIlroy-Young et al., 2020) — mismo enfoque
  de predecir jugadas al estilo humano a partir de partidas reales, no de autojuego.

---

## 7. Riesgos activos a vigilar durante estas 3 semanas

(Tomados del PAPs, sección 3.6 — los que más aplican a esta etapa)

- **Precisión de la visión por computadora** ante condiciones de luz variables — mitigar
  probando con fotos en distintas condiciones desde la semana 2, no dejarlo para el final.
- **Incompatibilidad entre versiones de librerías** — el `requirements.txt` fijado desde el
  día 1 existe justamente para esto.
- **Falta de experiencia del equipo en visión y aprendizaje automático** — por eso el orden del
  plan prioriza herramientas ya consolidadas (Stockfish, PyBullet) y deja lo más nuevo (visión,
  entrenamiento) con más tiempo de por medio y validación incremental.

---

## 8. Qué NO hacer en estas 3 semanas (fuera de alcance)

- No conectar el brazo físico real (depende del kit, todavía en trámite de importación).
- No intentar que el modelo "aprenda jugando" en producción — el reentrenamiento por lotes es
  una fase posterior, una vez que el modelo base esté entrenado y validado.
- No optimizar prematuramente el modelo de aprendizaje — el objetivo de estas 3 semanas es que
  el pipeline funcione de punta a punta, no que juegue perfecto.

---

## 9. Avance registrado (actualizado 2026-09-18)

Este documento quedó como el plan original de arranque; el seguimiento día a día real vive en
`docs/plan_sprints.md` (Sprint 1 cerrado, Sprint 2 en curso) y la arquitectura vigente está en
`PLAN_IMPLEMENTACION_COMPLETO.md` (el backend ya no usa la estructura `engine/`, `vision/`,
`learning/` de la sección 4 de este archivo — pasó a capas horizontales en español:
`backend/rutas/`, `backend/servicios/`, `backend/esquemas/`, `backend/modelos/`,
`backend/repositorios/`). Se deja acá un resumen corto para no tener que ir a buscarlo:

- **Sprint 1 — cerrado:** motor de Stockfish (`calcular_jugada`, `analizar_posicion`,
  `obtener_variaciones`), visión (reconocimiento de tablero + piezas, con la dama como pieza
  menos confiable todavía) y primer checkpoint entrenado del modelo propio en Colab.
- **Sprint 2 — en curso**, flujo del jugador completo en Flutter (onboarding, diagnóstico,
  configuración, partida, estadísticas). Últimos avances del lado backend:
  - `POST /partida` y `GET /partida/{id}` ahora requieren `Authorization: Bearer <token>` y
    asocian cada partida a su usuario (antes cualquiera podía ver cualquier partida).
  - Cada jugada aplicada se persiste en la tabla `jugada` (existía desde antes, pero no se
    poblaba) — es la base para calcular estadísticas y para el reentrenamiento por lotes (HU4)
    sin tener que recalcular todo con Stockfish cada vez.
  - Nuevos endpoints `GET /usuario/estadisticas` y `GET /usuario/historial-partidas` para el
    dashboard de progreso del jugador (HU14): partidas jugadas, ganadas/perdidas/tablas, racha
    de victorias e historial paginado, calculados al vuelo sin tabla de estadísticas separada.
  - Pendiente conocido: `top_errores` todavía devuelve vacío — clasificar blunder/error/
    inexactitud por jugada necesita guardar la evaluación de Stockfish al momento de jugar, que
    todavía no se agregó a la tabla `jugada`.

---

## 9. Avances completados — Sprint 2 (Backend track)

**Fecha**: 18/09/2026  
**Responsable**: Backend (FastAPI) — según coordinación en `COORDINACION_PARALELA_BACKEND_FLUTTER.md`

### ✅ HU10 — Auth obligatoria en partidas (ya verificado funcionando)
- `POST /partida` exige `Authorization: Bearer <token>` (reusa `get_current_user` de `ruta_auth.py`)
- Guarda `usuario_id` en `PartidaORM` al crear la partida
- `GET /partida/{id}` devuelve **403** si la partida no pertenece al usuario del token
- Tests: 401 (sin token), 403 (otro usuario), 200 (propio) — todos pasan

### ✅ HU6 — Soporte backend para análisis en vivo
- Agregado campo `variantes_candidatas` a `ResultadoMovimientoResponse` (`partida_esquema.py`)
- `mover()` en `servicio_partida.py` llama a `analizar_posicion()` tras cada jugada y devuelve las variantes
- Permite al frontend (Flutter) pintar barra Win% + indicador calidad en tiempo real sin llamar a `/analisis` aparte
- Test: `test_mover_partida_incluye_variantes_candidatas_para_hu6` pasa

### ✅ Poblar tabla `jugada` (clave para HU14 y HU4)
- `RepositorioPartidasEnMemoria` ahora persiste jugadas en memoria (antes era no-op)
- Métodos agregados a la interfaz `RepositorioPartidas`:
  - `obtener_jugadas_partida(partida_id)` → lista de jugadas con `{numero, fen_antes, movimiento, decidido_por}`
  - `listar_por_usuario(usuario_id)` → partidas filtradas por usuario
- Implementados en ambas versiones: memoria y Postgres
- Test: `test_repositorio_guarda_jugadas_en_memoria_para_hu14` verifica 4 jugadas (2 humano + 2 motor)

### ✅ HU14 — Endpoints de estadísticas
- `GET /usuario/estadisticas` → agregados calculados al vuelo:
  - `total_partidas`, `partidas_ganadas`, `partidas_perdidas`, `partidas_tablas`
  - `win_percent_promedio` (misma fórmula que frontend, sección 4.4 del contrato)
  - `racha_victoria_actual`
  - `top_errores`: clasifica blunder/error/inexactitud comparando eval humana vs mejor jugada Stockfish
- `GET /usuario/historial-partidas?limit&offset` → paginado con campos `{id, fecha, resultado, tipo_oponente, nivel, cantidad_jugadas}`
- Ambos requieren `Authorization: Bearer <token>` (mismo header que auth)
- Servicio nuevo `servicio_estadisticas_repo.py` usa Repository (funciona en memoria y Postgres)
- 5 tests nuevos pasan: 401 sin token, usuario nuevo (ceros/vacío), con partidas cuenta resultados

### ⏳ HU4 — Reentrenamiento Colab
- Pendiente: delegar a subagente `modelo-entrenamiento` (no bloquea lo anterior)

### 📋 Tests backend: **26 passed, 3 skipped** (vision por falta de cámara)

---

### Checkpoints de sincronización con Flutter (Nemotron)

| Checkpoint | Estado | Detalle |
|------------|--------|---------|
| 1. `POST /partida` guarda `usuario_id` | ✅ | Ya implementado antes de este sprint |
| 2. `GET /usuario/estadisticas` responde real | ✅ | **Completado** — endpoints funcionando en memoria, contrato sección 4.3 exacto |
| 3. Integración final punta a punta | ⏳ | Pendiente — levantar backend + Flutter contra él sin mocks |

El track Flutter puede conectar `StatsTab`/`ProgressTab`/`ProfileTab` a los endpoints reales usando la forma exacta del contrato (sección 4.3 de `COORDINACION_PARALELA_BACKEND_FLUTTER.md`).
