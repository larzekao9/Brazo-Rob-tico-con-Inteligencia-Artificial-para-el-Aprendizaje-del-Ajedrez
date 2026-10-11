# PLAN_MULTIJUGADOR.md — Jugar contra un amigo (salas con enlace) en `front_app/`

Plan de implementación para **Nemotron** (implementa backend y frontend). **Claude revisa** al
cerrar cada fase (ver §10). Contexto de proyecto: `CLAUDE.md`, `PLAN_FRONT_APP.md`.

> Esto es una **ampliación pedida explícitamente** por el equipo. El multijugador estaba como
> visión de tesis, fuera del plan de 3 semanas; se agrega aquí sin cambiar lo ya entregado.

---

## 1. Qué se construye

Desde **Inicio** de `front_app/`, el jugador puede:

1. **Crear una sala**: elige color (blancas / negras / al azar). La app le da un **código corto**
   (`K7M2QX`) y un **enlace** (`…/#/sala/K7M2QX`) para compartir. Espera en el tablero.
2. **Unirse** abriendo el enlace o escribiendo el código. Si el asiento libre existe, queda como
   segundo jugador y la partida empieza.
3. **Mirar**: cualquier otro usuario que abra el enlace con la sala ya llena entra como
   **espectador** (solo lectura). También hay un enlace explícito "para ver" (`?modo=ver`).
4. Al terminar (mate, tablas, abandono), la partida **queda guardada** en el backend y ambos
   jugadores ven un **análisis general de la partida hecho con Stockfish** (los dos bandos).

**Decisiones ya tomadas por el equipo:**
- Solo `front_app/` (no se toca `frontend/` ni `app_movil/`).
- **Los espectadores también son usuarios con cuenta** (todo el backend exige token).
- Las partidas contra un amigo **se guardan** (Postgres, como el resto de las partidas).
- El análisis es **general** (ambos bandos), con Stockfish.

**Fuera de alcance de esta entrega (Fase 2, no implementar ahora):** invitar por nombre de
usuario, ofrecer/aceptar tablas, reloj de partida real, WebSocket, chat, espectadores sin cuenta,
contador de espectadores, revancha.

---

## 2. Reglas del proyecto que NO se tocan

1. **Modelo propio / Stockfish (regla 1 de `CLAUDE.md`):** no cambia nada. En una partida entre
   humanos **no decide ninguna IA**. Stockfish solo se usa para el análisis posterior.
2. **Sin aprendizaje en vivo:** estas partidas no reentrenan nada.
3. Brazo físico: fuera. Sin `usa_brazo`, sin simulación 3D, sin cámara en estas partidas.
4. **Versiones exactas** en `requirements.txt`/`package.json` si se agrega algo (la idea es no
   agregar nada: no hay librerías nuevas en este plan).
5. Sin credenciales ni tokens en archivos del repo.
6. **Git:** commits simples describiendo el cambio, `feat(sala): …` / `feat(front_app): …`.
   **Prohibido** mencionar IA, asistentes o herramientas en commits o archivos, y prohibido
   `Co-Authored-By`. El autor es quien usa la sesión.
7. Tests: un test por módulo nuevo como mínimo (más abajo, lo mínimo exigido).
8. Archivos de **máximo ~400 líneas**; docstrings en funciones públicas (como el resto del backend).

---

## 3. Qué ya existe y se reutiliza (verificado en el código)

- La tabla `partida` ya persiste en Postgres cuando hay `DATABASE_URL` (Docker la tiene):
  `backend/repositorios/repositorio_partida.py`. **Una sala es una partida con código**: no se
  crea una tabla `sala` aparte.
- Columnas nuevas se agregan con el mecanismo de `backend/database.py` (`_COLUMNAS_AGREGADAS`,
  `ALTER TABLE … ADD COLUMN` al arrancar).
- `Partida` (`backend/modelos/partida.py`), `ciclo_vida.py`, `servicio_partida.py`,
  `ruta_partida.py` (patrón de rutas, `get_current_user`, `_a_estado`).
- `analisis_completo` (`servicio_partida.py`) ya evalúa **todas** las jugadas con Stockfish y
  devuelve por jugada `color`, `calidad`, `perdida_cp`, `evaluacion_cp`, `explicacion`, etc.
- Frontend: `TableroAjedrez`, `TableroDemo`, `HistorialJugadas`, `GraficoEvaluacion`,
  `ListaErrores` (Jugar), `GlassCard`, `BotonPrimario`, `PartidaPendiente` (Inicio), router por
  hash, `useSesion()`.

### Suposiciones del código actual que HAY que corregir para partidas humano-vs-humano

| Dónde | Suposición actual | Qué hacer |
|---|---|---|
| `Partida.jugadas_jugador` | "el humano siempre es blancas": `(n+1)//2` | En partidas `humano` no usar; contar plies totales |
| `servicio_partida.mover` | aplica jugada humana + responde la estrategia | **No tocar.** Crear `mover_humano` aparte |
| `ruta_partida._exigir_dueno` y `GET /partida/{id}` | solo el dueño (blancas) puede mover/leer | Las salas usan rutas `/sala/...` propias |
| `analisis_completo` | `es_jugador = i % 2 == 0` → textos "tu jugada / la contraparte" | Parámetro nuevo para análisis neutro (§6.3) |
| `crear_partida` → `cerrar_partidas_pendientes` | cierra TODAS las `en_curso` del usuario | **Excluir** partidas `humano` del cierre |
| `ciclo_vida.partida_en_curso_de`, `limpiar_partidas_inactivas` | miran `jugadas_jugador` y solo `usuario_id` | Ajustar para `humano` (§5.4) |
| Calibración, `GET /auth/nivel`, `/usuario/estadisticas` | miden al jugador **contra la IA** | **Excluir** `tipo_oponente == "humano"` (§5.5) |
| `GET /usuario/historial-partidas` | lista por `usuario_id` (solo blancas) | Incluir también las del jugador de negras, con rival y código |

---

## 4. Modelo de datos

### 4.1 `Partida` (dataclass) — campos nuevos
- `tipo_oponente = "humano"` (valor nuevo; **no** se agrega a `TIPOS_SOPORTADOS` de
  `fabrica_estrategias.py`, porque no hay estrategia: `POST /partida` debe seguir rechazándolo).
- `codigo_sala: str | None` — 6 caracteres, mayúsculas, alfabeto sin ambiguos
  (`ABCDEFGHJKMNPQRSTUVWXYZ23456789`, sin `0 O 1 I L`), **único**. Generar con `secrets.choice`.
- `usuario_blancas_id: int | None` y `usuario_negras_id: int | None`. `usuario_id` (dueño actual)
  se mantiene = quien creó la sala, para no romper listados.
- `estado` agrega el valor `"esperando"` (sala creada, falta el segundo jugador) a
  `ESTADOS_PARTIDA`. Flujo: `esperando → en_curso → terminada | abandonada`.
- `nivel` se guarda como `0` (no aplica); `control_tiempo_ms = 0` (sin reloj en Fase 1).

### 4.2 `PartidaORM` y migración
Columnas nuevas (todas opcionales, vía `_COLUMNAS_AGREGADAS`): `codigo_sala VARCHAR` (con índice
único donde no sea null), `usuario_blancas_id INTEGER`, `usuario_negras_id INTEGER`.
Actualizar `_partida_a_fila` / `_fila_a_partida` y el repositorio en memoria.
`RepositorioPartidas` agrega: `obtener_por_codigo(codigo)` (KeyError si no existe) y
`listar_por_participante(usuario_id)` (blancas **o** negras).

### 4.3 Reglas de color
Blancas = `usuario_blancas_id`, negras = `usuario_negras_id`. Al crear: el creador toma el color
elegido (si "aleatorio", `secrets.choice`). El otro asiento queda `None` hasta que alguien se una.

---

## 5. Backend — servicio y rutas

Archivos nuevos: `backend/servicios/sala/servicio_sala.py` (+ `test_servicio_sala.py`),
`backend/rutas/ruta_sala.py` (+ `test_ruta_sala.py`), `backend/esquemas/sala.py` (Pydantic).
Registrar el router en `backend/main.py` con prefijo `/sala`.

### 5.1 Endpoints (todos exigen `Authorization: Bearer`, `get_current_user`)

| Método y ruta | Quién | Qué hace |
|---|---|---|
| `POST /sala` body `{color: "blancas"\|"negras"\|"aleatorio"}` | cualquiera | Crea sala `esperando` con código. Devuelve `SalaResponse` |
| `POST /sala/{codigo}/unirse` | cualquiera | Si hay asiento libre y quien llama no es el creador → ocupa el asiento y la sala pasa a `en_curso`. Si ya está sentado → idempotente. Si la sala está llena → **no es error**: devuelve la sala con `rol: "espectador"` |
| `GET /sala/{codigo}` | cualquiera autenticado | Estado actual (para polling). Incluye `rol` de quien consulta |
| `GET /sala/{codigo}/jugadas-legales?casilla=` | jugador de turno o cualquiera | Mismo formato que `/partida/.../jugadas-legales` |
| `POST /sala/{codigo}/mover` body `{jugada: "e2e4"}` | **solo el jugador al que le toca** | Aplica la jugada, guarda, registra en `jugada`, detecta fin |
| `POST /sala/{codigo}/abandonar` | solo un jugador de la sala | Termina la partida; gana el otro |
| `GET /sala/{codigo}/analisis` | cualquiera autenticado, **solo si terminó** | Análisis general con Stockfish (§6.3) |
| `GET /sala/activa` | cualquiera | La sala `esperando`/`en_curso` más reciente del usuario, o `null` (para la tarjeta de Inicio). Declararla **antes** de `/{codigo}` |

Códigos HTTP: 404 código inexistente; 403 si espectador intenta mover/abandonar o mueve fuera de
turno ("No es tu turno"); 400 jugada ilegal / sala `esperando` (nadie contra quién jugar) /
partida ya terminada / análisis pedido antes de terminar; 409 al unirse al propio asiento si no
procede. Mensajes de error como **texto** (no listas/objetos), para que el front los muestre.

### 5.2 `SalaResponse` (contrato con el frontend — no cambiar nombres sin avisar)
```json
{
  "codigo": "K7M2QX",
  "partida_id": "…hex…",
  "estado": "esperando | en_curso | terminada | abandonada",
  "fen": "…", "turno": "blancas | negras",
  "jugadas": ["e4", "e5"],          // SAN
  "ultima_jugada_uci": "e7e5",       // null si no hay
  "terminada": false, "resultado": null,   // "1-0" | "0-1" | "1/2-1/2"
  "motivo_fin": null,                // "mate" | "tablas" | "abandono" | null
  "blancas": {"id": 3, "nombre": "Luis", "avatar_url": null},   // null si el asiento está libre
  "negras":  null,
  "rol": "blancas | negras | espectador",   // de QUIEN consulta
  "version": 7                       // = cantidad de plies + indicador de estado; sube con cada cambio
}
```
**No exponer** emails ni ids de usuarios que no sean los dos jugadores. Nombre y avatar sí.

### 5.3 `servicio_sala` (funciones pequeñas, probables sin cámara ni modelo)
`crear_sala(usuario_id, color)`, `unirse(codigo, usuario_id)`, `obtener_estado(codigo, usuario_id)`,
`mover_humano(codigo, usuario_id, jugada_uci)`, `abandonar(codigo, usuario_id)`,
`analisis_sala(codigo, rango)`, `sala_activa_de(usuario_id)`.
`mover_humano`: valida turno por color contra el asiento del usuario; `tablero.parse_uci`;
aplica; `registrar_jugada(..., decidido_por="jugador")`; actualiza `iniciada_en`/`actualizada_en`;
si `tablero.is_game_over()` → `estado="terminada"`; guarda. Sin Stockfish, sin estrategia, sin
brazo. Usar bloqueo por partida (un `threading.Lock` por `partida_id`) para que dos jugadas
simultáneas no se pisen.

### 5.4 Ciclo de vida
- `esperando` sin segundo jugador por más de **30 min** → se elimina (nadie llegó).
- `en_curso` humano sin jugadas por **60 min** → se elimina; con jugadas e inactiva **12 h** →
  `abandonada` (mismas constantes que hoy; que `jugadas_jugador` no se use para `humano`: contar
  `len(tablero.move_stack)`).
- `cerrar_partidas_pendientes` **no cierra** salas `humano` al crear una partida contra la IA, ni
  viceversa. `partida_en_curso_de` (retomar contra IA) **ignora** `humano`; las salas se retoman
  desde `GET /sala/activa`.

### 5.5 Exclusiones (estas partidas no miden contra la IA)
Excluir `tipo_oponente == "humano"` de: calibración por partida (`/partida/{id}/calibrar`,
`GET /auth/nivel`, diagnóstico de 3 partidas) y de `/usuario/estadisticas` (precisión promedio,
victorias, racha, top errores). **Sí** aparecen en `GET /usuario/historial-partidas` (para ambos
jugadores) con campos nuevos `rival_nombre`, `codigo_sala`, `color` (`"blancas"|"negras"`) y
`resultado` (`1-0`/`0-1`/`1/2-1/2`); el front calcula victoria/derrota según el color.
Verificar con el test que una partida humano-vs-humano **no cambia** el nivel del jugador.

---

## 6. Análisis general con Stockfish

### 6.1 Requisito
Un análisis **neutro, de los dos bandos**, disponible para los dos jugadores **y** los
espectadores cuando la partida terminó.

### 6.2 Cómo
Reutilizar `analisis_completo(partida_id, rango=…)`: ya devuelve cada jugada con `color`,
`calidad`, `perdida_cp`, `evaluacion_cp`, `mate_en`, `explicacion`. Agregar parámetro
`perspectiva: "jugador" | "neutra" = "jugador"`; con `"neutra"`, `explicar_jugada` recibe el texto
en tercera persona ("Las blancas…/Las negras…") en vez de "tú / la contraparte". **No cambiar el
comportamiento por defecto** (los tests existentes deben seguir pasando).
`rango` = rango del usuario que consulta (como hoy).

### 6.3 `GET /sala/{codigo}/analisis` devuelve
```json
{
  "codigo": "K7M2QX",
  "resultado": "1-0", "motivo_fin": "mate", "total_jugadas": 41,
  "blancas": {"nombre": "Luis", "precision": 74.2, "mejores": 9, "imprecisiones": 4, "errores": 2, "blunders": 1},
  "negras":  {"nombre": "Ana",  "precision": 61.0, "mejores": 6, "imprecisiones": 5, "errores": 3, "blunders": 2},
  "curva": [ {"ply": 1, "evaluacion_cp": 25, "mate_en": null}, … ],  // desde las blancas
  "momentos_clave": [ {"ply": 17, "color": "negro", "jugada_san": "Qxb2", "calidad": "blunder",
                       "perdida_cp": 420, "mejor_jugada_san": "Nf6", "explicacion": "…"} ],  // los 5 mayores
  "jugadas": [ … lista completa de analisis_completo … ]
}
```
Precisión por bando: promedio de la calidad/precisión **por jugada de ese bando** (impares =
blancas, pares = negras); reutilizar el mismo cálculo que usa `generar_resumen_partida` para
`precision_jugador`, aplicado a cada bando por separado (no duplicar la fórmula).
Cache: guardar el resultado la primera vez (columna JSON/Text `analisis_json` en `partida`, o
memoria del proceso como mínimo) — Stockfish tarda ~10 s en 70 jugadas y lo piden 2+ usuarios.
Ojo: `analisis_completo` hoy **persiste** las evaluaciones por jugada y no debe invocar
calibración para `humano` (§5.5).
**Bug conocido a no heredar:** `analisis_completo` marca como `blunder` la jugada que da mate
(`mate_en == 0`) y baja la precisión; en el análisis de sala tratar `mate_en == 0` del bando que
jugó como jugada brillante, y probarlo con un test (mate del pastor).

---

## 7. Frontend `front_app/`

### 7.1 Rutas nuevas (agregar a `src/router.ts` y `src/paginas/registro.ts`)
`/amigo` (crear o unirse), `/sala/:codigo` (esperando, jugando, espectador, terminada),
`/sala/:codigo/analisis`. Nav inferior: `/sala/*` y `/amigo` ocultan la barra (como
`/jugar/partida/:id`, ver `SIN_NAVEGACION` en `App.tsx`) o resaltan Inicio — decidir y documentar.

### 7.2 Archivos
```
front_app/src/api/sala.js              # crearSala, unirseASala, obtenerSala, moverEnSala,
                                       # abandonarSala, analisisSala, salaActiva, jugadasLegalesSala
front_app/src/paginas/Amigo/
  Amigo.tsx          # dos tarjetas: "Crear sala" (selector de color) y "Unirme con código"
  Sala.tsx           # orquesta los 4 estados (esperando / jugando / espectador / terminada)
  useSala.ts         # polling de GET /sala/{codigo}
  SalaEsperando.tsx  # código grande, enlace, copiar, compartir (navigator.share si existe)
  SalaTablero.tsx    # tablero + nombres + turno + historial + abandonar
  SalaAnalisis.tsx   # análisis general (ambos bandos)
```
Reutilizar `TableroAjedrez` (`colorJugador` = rol; para espectador **no pasar** `colorJugador` →
solo lectura), `HistorialJugadas`, `GraficoEvaluacion`, `ListaErrores`, `GlassCard`,
`BotonPrimario`, `Chip`. Sin librerías nuevas, solo tokens de Tailwind, mobile-first.

### 7.3 Comportamiento
- **Polling** cada 1.5 s a `GET /sala/{codigo}` **solo mientras la pestaña está visible**
  (`document.visibilityState`), y se **detiene** cuando `terminada`. Usar `version` para no
  re-renderizar si no cambió. Limpiar `setInterval`/listeners al desmontar. Cancelar con
  `AbortController` o bandera `activo` (patrón ya usado en `Resultado.tsx`).
- **Orientación:** el tablero se orienta según el color del jugador (negras abajo si juega
  negras); el espectador ve desde las blancas.
- **Mover:** dos toques (origen → destino) como en `Partida`; bloqueado si no es tu turno;
  promoción con `SelectorPromocion`; tras mover, **actualización optimista** (mostrar la jugada
  ya) y reconciliar con la respuesta/siguiente poll; si el backend rechaza, revertir y mostrar el
  mensaje.
- **Esperando:** mostrar código y enlace con botones copiar/compartir (`navigator.clipboard` en
  `try/catch`; fallback para seleccionar el texto). Al unirse el rival, pasa a jugar solo (por el poll).
- **Unirse con código:** normalizar a mayúsculas y recortar espacios; 404 → "No existe esa sala".
- **Espectador:** banner fijo "Estás viendo esta partida" + nombres de ambos jugadores; no hay
  botones de mover ni abandonar.
- **Terminada:** tarjeta con resultado y motivo; botón "Ver análisis" (`/sala/:codigo/analisis`)
  y "Volver al inicio". **Dos jugadores y espectadores** ven el análisis.
- **Análisis:** carga con spinner ("Analizando con Stockfish…, puede tardar unos segundos");
  precisión de blancas vs negras, curva, momentos clave con tablero (`TableroDemo` con `fen_antes`),
  lista de jugadas con badge de calidad. Mismo cuidado con `mate_en` que en `Resultado.tsx`.
- **Enlace profundo con login:** si abren `#/sala/ABC123` sin sesión, el guardia redirige a
  `/login`; guardar la ruta en `sessionStorage` (en `try/catch`) y **volver a ella tras
  iniciar sesión o registrarse**. Hoy esto no existe: se agrega en `App.tsx`/`SesionContext`
  sin romper la redirección actual. Tras volver, hacer `POST /unirse` automáticamente.
- **Inicio** (`paginas/Inicio/Inicio.tsx`, archivo ya existente): agregar botón **"Jugar con un
  amigo"** junto a "Jugar", y una tarjeta de **sala activa** (como `PartidaPendiente`) si
  `GET /sala/activa` devuelve algo: "Sala K7M2QX · esperando rival" / "Partida con Ana en curso" →
  botón **Entrar**. En `esperando`, botón secundario **Cancelar sala** (si no existe endpoint,
  usar `abandonar`; documentar y pedir al backend un `DELETE`/cancelar si hace falta).
- **Historial** (`paginas/Historial/Historial.tsx`): mostrar las partidas con amigo como
  "vs {rival_nombre}", victoria/derrota según color, y abrir `/sala/:codigo/analisis` en vez de
  `/jugar/resultado/:id`.

### 7.4 Infra del front (olvidable, pero rompe todo si falta)
- `front_app/vite.config.ts`: agregar `'/sala': BACKEND_URL` al proxy.
- `front_app/nginx.conf`: agregar `sala` a la expresión regular de prefijos (`location ~ ^/(…)`).
- Si algo del backend requiere `docker compose build backend`, avisar: reiniciar el backend en
  Docker recrea el contenedor (las partidas **sí** persisten porque están en Postgres).

---

## 8. Pruebas mínimas exigidas

**Backend (`pytest`, sin cámara ni modelo):**
- Crear sala: código de 6 caracteres válidos y único; color "aleatorio" asigna uno.
- Unirse: segundo jugador entra y la sala pasa a `en_curso`; el creador no puede ocupar ambos
  asientos; un tercer usuario recibe `rol: "espectador"`; unirse dos veces es idempotente.
- Mover: solo el del turno; fuera de turno 403; espectador 403; jugada ilegal 400; sala
  `esperando` 400; fin por mate marca `terminada` y `resultado`.
- Abandonar: gana el otro; persiste.
- Persistencia: tras "reiniciar" el repositorio (nuevo repositorio sobre la misma BD de prueba), la
  sala y las jugadas siguen.
- Exclusión: una partida `humano` terminada no cambia `GET /auth/nivel` ni `/usuario/estadisticas`
  y no cierra una partida contra la IA ni es cerrada por ella.
- Análisis: 400 antes de terminar; tras mate del pastor devuelve ambos bandos, `mate_en == 0` no
  sale como blunder; segunda llamada usa caché.
- Ciclo de vida: `esperando` viejo se elimina; `en_curso` humano inactivo pasa a `abandonada`.
- Regresión: `pytest backend` completo sigue en verde (no romper partidas contra la IA).

**Frontend:** `npm run lint` y `npm run build` limpios.

**Prueba de punta a punta (la hace el revisor, §10):** dos usuarios reales distintos
(`jugador@test.com` y `jugador@kairos-chess.ai`, ver `docs/usuarios_locales_dev.md`) en dos
perfiles/ventanas, más un tercero como espectador.

---

## 9. Fases y orden de trabajo

Cada fase termina con **commit** (sin push hasta la revisión, salvo que se indique) y se marca
`[x]` aquí. **No pasar a la siguiente fase sin la revisión de la anterior.**

### Fase 1 — Backend núcleo
- [ ] Modelo + ORM + migración + repositorio (`obtener_por_codigo`, `listar_por_participante`).
- [ ] `servicio_sala` y `ruta_sala` con `POST /sala`, `/unirse`, `GET /sala/{codigo}`, `/jugadas-legales`,
      `/mover`, `/abandonar`, `GET /sala/activa`.
- [ ] Ciclo de vida y exclusiones (§5.4–5.5) y campos nuevos en `historial-partidas`.
- [ ] Tests de §8 (todo lo de backend salvo análisis). `pytest backend` en verde.
- **Listo cuando:** dos usuarios juegan una partida completa **solo con curl**.

### Fase 2 — Backend análisis
- [ ] `perspectiva="neutra"` en `analisis_completo` / `explicar_jugada` (sin romper lo existente).
- [ ] `GET /sala/{codigo}/analisis` con caché y el contrato de §6.3 + tests.

### Fase 3 — Frontend núcleo
- [ ] `api/sala.js`, rutas, proxies (`vite.config.ts`, `nginx.conf`).
- [ ] `Amigo`, `Sala` (esperando/jugando/espectador/terminada) con polling, enlace profundo con
      login, botón y tarjeta en Inicio.
- **Listo cuando:** dos navegadores juegan una partida completa en `localhost:8081`.

### Fase 4 — Frontend análisis e historial
- [ ] `SalaAnalisis`, historial con rival y análisis por sala.

### Fase 5 — Cierre
- [ ] Reconstruir imágenes (`docker compose up -d --build backend front_app`), probar en Docker.
- [ ] Marcar este plan y actualizar `docs/plan_sprints.md`. Actualizar el grafo del repo y push.

---

## 10. Revisión (rol de Claude)

Claude revisa **después de cada fase**, antes de que Nemotron siga. Qué se revisa y qué bloquea
el avance:

**Checklist backend (fases 1–2)**
- [ ] ¿`POST /partida` sigue rechazando `humano`? ¿`TIPOS_SOPORTADOS` intacto?
- [ ] ¿Solo el jugador del turno puede mover? ¿Espectador 403? ¿Concurrencia (dos movimientos a la vez)?
- [ ] ¿Ningún email/id ajeno en las respuestas? ¿Códigos con alfabeto sin ambiguos y `secrets`?
- [ ] ¿Las exclusiones de §5.5 realmente funcionan (probado con test)? ¿El nivel del jugador no cambia?
- [ ] ¿`cerrar_partidas_pendientes` y la limpieza no matan salas activas?
- [ ] ¿Comportamiento por defecto de `analisis_completo` intacto (tests existentes en verde)?
- [ ] ¿Migración idempotente sobre una BD que ya existe (Docker)? ¿Persiste tras reiniciar?
- [ ] ¿Docstrings, tests, ningún archivo >400 líneas?

**Checklist frontend (fases 3–4)**
- [ ] Polling se detiene al terminar, al ocultar la pestaña y al desmontar (sin fugas).
- [ ] Espectador realmente solo lectura (no puede ni seleccionar piezas).
- [ ] Enlace profundo: sin sesión → login → vuelve a la sala y se une.
- [ ] Mensajes de error legibles (sin "[object Object]"), estados de carga/vacío/error.
- [ ] Sin `#hex` fuera de `index.css`, sin librerías nuevas, `lint` y `build` limpios.
- [ ] Responsive 360/375/430 px y escritorio.

**QA de punta a punta (Claude lanza `qa-reviewer`):** crear sala, compartir enlace, unirse con
otro usuario, jugar hasta mate, abandono, espectador (tercer usuario) viendo en vivo, análisis,
historial de ambos, sala `esperando` abandonada, recarga a mitad de partida, backend caído.

**Qué bloquea:** cualquier fuga de datos entre usuarios, que un espectador pueda mover, que la
partida humana afecte el nivel/estadísticas contra la IA, o que se rompan las partidas contra la
IA. Lo demás se corrige en un commit de seguimiento.

---

## 11. Riesgos

| Riesgo | Mitigación |
|---|---|
| Polling a 1.5 s con muchos espectadores carga el backend | `GET /sala` barato (sin Stockfish), pausa en pestaña oculta; Fase 2: WebSocket |
| Reinicio del backend (Docker) | Las partidas están en Postgres; no hay estado crítico solo en memoria. Reanudan por polling |
| Dos movimientos simultáneos | Lock por partida en `mover_humano` + validación de turno |
| Adivinar códigos | 31⁶ ≈ 887 millones de combinaciones y exige sesión; si hace falta, limitar intentos de `unirse` |
| Análisis lento (≈10 s en 70 jugadas) | Caché por partida; spinner con mensaje; solo se calcula al pedirlo |
| Confundir las estadísticas contra IA con las humanas | Exclusión explícita y probada (§5.5) |
| Jugador abandona/desaparece | `abandonar` manual; tras 12 h sin jugadas pasa a `abandonada` |

---

## 12. Pedidos entre agentes
*(Vacío. Formato: `[Nemotron→Claude]` / `[Claude→Nemotron]`, fecha, qué se pide, estado.)*

---

## 13. Cierre (regla de `CLAUDE.md`)
Tests relevantes en verde → actualizar el grafo de conocimiento del repo → `commit` + `push`.
