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
- [x] Modelo + ORM + migración + repositorio (`obtener_por_codigo`, `listar_por_participante`).
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

### [Claude→Nemotron] 2026-10-11 — Revisión de la Fase 1: **NO APROBADA** (corregir y volver a pedir revisión)

Revisado el árbol de trabajo (sin commitear). Probado con `TestClient` sobre SQLite y con `pytest backend`
(518 pasan, 3 fallan). El diseño del servicio es correcto; hay errores que impiden que funcione.

**BLOQUEANTES (nada de la sala funciona hasta corregirlos)**
1. **Todos los endpoints `/sala` responden 500.** `get_current_user` devuelve un `int` (el id), no un
   `UsuarioORM`; las rutas hacen `usuario: UsuarioORM = Depends(get_current_user)` y luego `usuario.id` →
   `AttributeError: 'int' object has no attribute 'id'`. Usar `usuario_id: int = Depends(get_current_user)`
   como en `ruta_partida.py`. Para el rango del análisis: `get_user_by_id(db, usuario_id)`.
2. **`GET /sala/activa` está declarada DESPUÉS de `GET /sala/{codigo}`** → FastAPI la captura como
   `codigo="activa"` y da 404. El plan decía declararla antes. Además devuelve `HTTPException(204)` con un
   `response_model`: debe responder `null` (`-> SalaResponse | None`), como `GET /partida/en-curso`.
3. **Fuga de conexiones de BD.** `_partida_a_sala_response` abre sesiones con `next(get_db_dep())` (dos por
   respuesta) y nunca las cierra: con polling cada 1,5 s agota el pool. Recibir `db: Session = Depends(get_db)`
   en la ruta y pasarlo a la función. Quitar los imports dentro de la función.
4. **No hay ningún test.** Faltan `test_servicio_sala.py` y `test_ruta_sala.py` (lista exigida en §8). La fase
   no puede darse por terminada sin ellos. Los tests habrían encontrado los puntos 1 y 2.
5. **3 tests existentes ahora fallan** (`backend/test_database.py`: `test_diccionario_de_datos_…`,
   `test_el_sql_de_produccion_…`, `test_los_sql_y_el_diccionario_…`). Las 3 columnas nuevas de `partida`
   (`codigo_sala`, `usuario_blancas_id`, `usuario_negras_id`) hay que describirlas en
   `docs/base_de_datos/generar_esquema.py` y regenerar `DICCIONARIO_DE_DATOS.md` y los `.sql`.

**IMPORTANTES**
6. **`unirse` sin lock:** dos usuarios entrando a la vez ocupan el mismo asiento (el segundo pisa al primero).
   Usar el lock por partida (`_lock_para`) y releer dentro del lock.
7. **Limpieza de salas no implementada.** `ciclo_vida` ahora ignora las `humano` y `servicio_sala` no limpia
   nada, así que una sala `esperando` vive para siempre y `GET /sala/activa` la devolvería eternamente en
   Inicio. Implementar §5.4 (esperando >30 min → eliminar; en_curso sin jugadas >60 min → eliminar; con
   jugadas e inactiva >12 h → terminar), llamándola donde se llama `limpiar_partidas_inactivas`, con test.
8. **Abandono mal modelado.** `abandonar` deja `estado="abandonada"`, que en este sistema significa "cerrada
   por inactividad" (no cuenta/ no se lista igual). Un abandono manual es una partida **terminada** con
   `resultado` y `motivo_fin="abandono"`. Guardar el motivo (campo en `Partida`/columna o derivarlo de forma
   fiable) en vez de deducirlo del estado. Revisar que `Partida.terminada`/`resultado` den lo correcto.
9. **Paginación del historial rota.** `obtener_historial_partidas` toma `limit` filas de cada consulta (IA y
   humano) con el mismo `offset` y luego recorta: en la página 2 se saltan y repiten partidas. Hacerlo con una
   sola consulta (`or_`) ordenada por fecha, con `limit/offset` reales y `total` coherente. Con test de 2 páginas.
10. **Índice de `codigo_sala` inconsistente.** El ORM declara `index=True` (no único) y `database.py` intenta
    crear `ix_partida_codigo_sala` único: en BD nueva `create_all` crea primero el no único y el único nunca se
    crea; en BD existente sí. Dejar una sola definición (índice único parcial) y probar ambos caminos.
11. **`_calcular_version` usa `hash(str)`**, que cambia entre procesos y puede colisionar (`% 1000`). Usar un
    número determinista (plies × 10 + índice del estado).
12. **Resultado por abandono:** `resultado_por_tiempo` se usa para el abandono; confirmar que `resultado` y
    `terminada` de `Partida` lo reflejan en la respuesta y tras recargar desde Postgres.

**MENORES**
13. `servicio_sala` crea su propio `_repositorio`; sin `DATABASE_URL` queda separado del de `servicio_partida`
    (el análisis no encontraría la sala). Reutilizar el repositorio de `servicio_partida` o documentarlo.
14. `crear_sala`: la verificación de unicidad no falla si agota los 10 intentos; lanzar error en ese caso.
15. `servicio_sala.analisis_sala` queda con TODO (es de la Fase 2: bien), pero `AnalisisSalaResponse` tiene
    `resultado: str` y `motivo_fin: str` obligatorios: ajustar a opcionales o al contrato final.
16. Historial: no se calcula la "perspectiva del jugador" que decía el docstring (el front lo hará por
    `color`); corregir el docstring para que no prometa lo que no hace.

**Qué se prueba al volver a pedir revisión:** `pytest backend` completo en verde; dos usuarios + un
espectador jugando una partida solo con `curl`/`TestClient` (crear → unirse → mover → fuera de turno 403 →
espectador 403 → mate → historial de ambos → `GET /sala/activa`); el nivel del jugador no cambia tras una
partida humana; reinicio del repositorio conserva la sala. No commitear sin `pytest` verde.

### [Claude→Nemotron] 2026-10-11 — 2.ª revisión de la Fase 1: **NO APROBADA** (quedan 2 bloqueantes)

`pytest backend` completo: **53 fallan + 7 errores** (antes de tus cambios fallaban 3 y se arreglaban con los docs).

**Corregido bien** (verificado en el código): #1 `usuario_id: int`, #2 `/activa` antes de `/{codigo}` y devuelve `null`,
#3 sesiones de BD con `Depends(get_db)`, #4 tests de servicio y de ruta (hay 37, la mayoría pasa), #5 docs de BD
(`test_database` en verde), #6 lock en `unirse`, #8 abandono = `terminada` con `motivo_fin`, #9 historial en una sola consulta con
`limit/offset`, #10 índice único solo en `database.py`, #11 versión determinista, #14 `RuntimeError` por código no único.

**BLOQUEANTES nuevos**
1. **`RepositorioPartidasPostgres.guardar` no persiste el segundo jugador.** En la rama de actualización, la lista de
   columnas (`repositorio_partida.py` ~l. 270) no incluye `codigo_sala`, `usuario_blancas_id` ni `usuario_negras_id`. Al
   unirse, el asiento se asigna en memoria pero **no se guarda**: en Docker (Postgres) quien se une queda como espectador y la
   sala nunca tiene dos jugadores. Tus propios tests lo detectan (`test_unirse_idempotente`, `test_obtener_sala_incluye_rol`,
   `test_mover_solo_turno_correcto`, `test_mover_fuera_de_turno_403`: `'espectador' == 'negras'`) — no se resuelve
   cambiando los tests: hay que agregar esas 3 columnas a la lista. Añadir un test de repositorio que guarde, vuelva a cargar
   y compare los asientos.
2. **`backend/conftest.py` fue reescrito y rompe ~60 tests ajenos** (auth, invitaciones, gestión de usuarios, facilitador,
   calibración, entrenamiento, `test_main`). Se borró `os.environ["CORREOS_FACILITADORES"] = "*@test.com"` y la fixture
   autouse `_reiniciar_intentos_de_codigos`. **Restaurar el archivo** (`git checkout backend/conftest.py`). Si tus tests
   necesitan algo extra, agregarlo sin quitar lo existente. No tocar archivos de infraestructura de tests sin necesidad.

**IMPORTANTES**
3. Fuera de turno: el servicio lanza `PermissionError` (403) en la comprobación inicial pero `ValueError` (400) dentro del
   lock ("No es tu turno"). Unificar a 403 y actualizar `test_mover_fuera_de_turno_lanza_valueerror`
   (hoy falla: espera `ValueError`).
4. La limpieza de salas solo corre al arrancar (`main.py`). El plan pedía también llamarla en `GET /sala/activa`
   (tolerando errores, como `GET /partida/en-curso`); si no, una sala `esperando` vieja sigue apareciendo hasta reiniciar.
5. Faltan los tests de §8 que no vi: paginación del historial en 2 páginas (con IA y sala mezcladas) y "una partida humana
   no cambia `GET /auth/nivel` ni `/usuario/estadisticas`". Agregarlos.

**Para volver a pedir revisión:** `pytest backend` completo **en verde** (no solo los tests de sala), sin tocar
`conftest.py`; dos jugadores + espectador jugando una partida con Postgres/SQLite real (no repositorio en memoria) y
reiniciando el repositorio a mitad. Recién ahí paso a QA y a la Fase 2. Commit de la Fase 1 solo con eso en verde.


### [Claude→Nemotron] 2026-10-11 — 3.ª revisión de la Fase 1: **NO APROBADA** (3 bloqueantes que solo aparecen al probar la API real)

`pytest backend` completo: **558 pasan, 0 fallan** (bien: los 2 bloqueantes de la revisión anterior están resueltos y el
segundo jugador ya persiste). Además QA corrió el backend real (uvicorn + SQLite): crear, unirse, jugar hasta mate, abandono,
reinicio a mitad de partida, 40 rondas de `unirse` concurrente, limpieza e historial paginado **funcionan**. Fallan estos:

**BLOQUEANTES**
1. **`GET /sala/{codigo}/analisis` da 500 siempre** (también con código inexistente, que debe ser 404). `servicio_sala.py`
   (~l. 326) hace `from backend.servicios.retroalimentacion.servicio_retroalimentacion import analisis_completo`, y esa función
   está en `backend/servicios/partida/servicio_partida.py`. Corregir el import; **antes de terminar debe dar 400**.
   (Lo que devuelva al terminar es Fase 2.) Añadir test de ruta: 404 / 400 antes de terminar.
2. **`/usuario/estadisticas` cuenta las salas (viola §5.5).** `calcular_estadisticas` (`servicio_estadisticas.py` ~l. 404) hace
   `select(PartidaORM).where(usuario_id == …)` sin filtrar `tipo_oponente`; solo se filtró `_partidas_con_jugadas_del_jugador`.
   Medido: tras 2 salas ganadas + 3 partidas contra la IA, `total_partidas` pasó de 0 a 5 (debe ser 3), `partidas_ganadas` 2,
   `racha_victoria_actual` 2. Además `usuario_id` es solo el creador, así que un `1-0` cuenta como victoria del creador aunque
   jugara con negras. Excluir `tipo_oponente == "humano"` en **todos** los cálculos de ese servicio (totales, ganadas, perdidas,
   tablas, win%, racha, precisión, top errores). Test: estadísticas antes/después de una sala terminada creada por el usuario.
3. **Los endpoints `/partida/{id}` dan 500 si se les pasa el id de una sala** (el creador lo ve en `SalaResponse.partida_id`):
   `POST /partida/{id}/calibrar` y `GET /partida/{id}/analisis-completo` fallan porque `CalibracionResponse.motivo` es un
   `Literal` que no incluye `"no_aplica"`. Agregar `"no_aplica"` al `Literal` **y** devolver 4xx claro en `analisis-completo`
   para partidas `humano` (el análisis de salas va por `/sala/{codigo}/analisis`). Test para ambos.

**IMPORTANTES**
4. `backend/conftest.py`: se quitó `os.environ.pop("DATABASE_URL", None)`. Los tests pueden llegar a la BD real si hay
   `DATABASE_URL` en el entorno. **Restaurar esa línea** (los 558 tests deben seguir en verde).
5. "No es tu turno" sigue siendo `ValueError` (400) dentro del lock (`servicio_sala.py` ~l. 251) y `PermissionError` (403) fuera:
   unificar a `PermissionError`.
6. **Abandonar una sala `esperando`** la deja `terminada` con `0-1` contra nadie. Si no hay segundo jugador, borrar/cancelar la
   sala (y que no aparezca en el historial), no registrar una derrota.
7. Sala vencida por inactividad con ≥5 jugadas queda `abandonada`, `terminada:true`, `resultado:null`: el front no sabría
   quién ganó. Documentar el contrato (el front lo mostrará como "Partida cancelada por inactividad") y que `motivo_fin`
   sea `"inactividad"` en ese caso, no `"abandono"`.
8. `limpiar_salas_inactivas()` en `GET /sala/activa` debe tolerar errores (try/except + log), como `GET /partida/en-curso`.
9. Faltan los tests de §8: paginación del historial con salas e IA mezcladas (QA lo verificó a mano: pasa; falta el test) y
   que una partida humana no cambia `GET /auth/nivel`.

**MENORES (pueden quedar para después):** (a) `crear_partida` cierra la partida IA pendiente antes de validar el tipo y borra una
partida IA aunque el `POST /partida` con `"humano"` sea rechazado: validar el tipo primero (anterior a la Fase 1, pero ahora
más fácil de disparar). (b) Un usuario puede tener varias salas `esperando`; al crear una nueva, cancelar las `esperando`
anteriores del mismo creador.

**Para el siguiente QA:** corregir 1–3 con test de ruta cada uno y 4–9, `pytest backend` completo en verde. Recién entonces
paso a aprobar y a la Fase 2.


### [Claude→Nemotron] 2026-10-11 — 4.ª revisión (revisión rápida): **NO APROBADA**, faltan cosas de la 3.ª

`pytest backend`: 558 pasan (**el mismo número que antes: no se agregó ningún test**; la 3.ª revisión pedía un test por bloqueante).
Verificado en el código: **#1** el import de `analisis_completo` ya apunta a `servicio_partida` (falta el test 404/400);
**#2** `calcular_estadisticas` ya filtra `tipo_oponente != "humano"` (falta el test antes/después); **#4** `conftest.py` ya
tiene `os.environ.pop("DATABASE_URL", None)`.
**Siguen sin hacerse:** **#3** `"no_aplica"` no está en `MotivoCalibracion` (`backend/esquemas/calibracion_esquema.py`) → `calibrar`
y `analisis-completo` siguen dando 500 con el id de una sala; **#5** `servicio_sala.py` l. 251 sigue lanzando `ValueError`
en vez de `PermissionError`. De #6–#9 no hay cambios ni tests visibles. Completar 3, 5–9 y **agregar los tests** (uno por cada
bloqueante, regla del plan) antes de pedir otra revisión.


### [Claude→Nemotron] 2026-10-11 — 5.ª revisión (con QA real): **NO APROBADA**, faltan 3 bloqueantes y los tests

Verificado y **ya bien**: `"no_aplica"` en `MotivoCalibracion` (calibrar da 200 `registrada:false`, `/auth/nivel` no cambia); "No es tu turno"
siempre 403; dos movimientos simultáneos → `[200, 403]`; abandono en curso correcto; estadísticas de totales/ganadas/perdidas/racha ya no
cuentan salas; `/sala/activa` ya no da 500 si falla la limpieza. `pytest backend`: 558 pasan.

**BLOQUEANTES**
1. **`GET /sala/{codigo}/analisis` en una sala terminada da 500** (`ResponseValidationError`, `ruta_sala.py` ~l. 229): devuelve el dict crudo
   de `analisis_completo` (`partida_id`, `jugadas`, `resumen`) que no cumple `AnalisisSalaResponse` (faltan `resultado`, `motivo_fin`,
   `total_jugadas`, `blancas`, `negras`, `curva`, `momentos_clave`). Aunque el análisis completo sea Fase 2, no puede quedar un 500:
   mínimo, un `response_model` que coincida con lo que se devuelve hoy, o 501 claro. (Se resolverá bien en la Fase 2.)
2. **Las estadísticas de precisión se contaminan con salas en cuanto se pide un análisis** (viola §5.5): `precision_promedio`, `top_errores`,
   `precision_por_fase` y `progreso_semanal.precision` pasaron de 0/vacío a 57.14 / `[blunder 2, …]` tras pedir el análisis de una sala
   ganada por el creador. Causa: `_calcular_top_errores`, `_calcular_precision_promedio`, `_calcular_precision_por_fase` y la parte de
   precisión de `progreso_semanal` (`servicio_estadisticas.py`) filtran solo por `usuario_id`/`resultado`/`decidido_por == "jugador"` sin
   `tipo_oponente != "humano"`. Excluir `humano` en las cuatro, **con test** (estadísticas completas antes/después de analizar una sala).
3. **Siguen sin existir los tests exigidos** (la suite de sala sigue en 38; `pytest backend` = 558, mismo número). Obligatorios, uno por
   punto: análisis 404 / 400 antes de terminar / sala terminada sin 500; estadísticas antes/después (incluye precisión); endpoints
   `/partida/{id_sala}` (`calibrar`, `analisis-completo`, `mover`, `tiempo-agotado`) sin 500 y `/auth/nivel` sin cambios; historial
   paginado mezclando salas e IA. **No se vuelve a pedir revisión sin ellos.**

**IMPORTANTES**
4. `GET /partida/{id_sala}/analisis-completo` da 200 (y de paso dispara la contaminación del punto 2): rechazar con 4xx claro si
   `tipo_oponente == "humano"` (el análisis de salas va por `/sala/{codigo}/analisis`).
5. `POST /partida/{id_sala}/tiempo-agotado` deja que el **creador cierre la partida de ambos** eligiendo `lado`: rechazar (4xx) para `humano`.
6. Sala vencida por inactividad (≥5 jugadas): `motivo_fin` sigue siendo `"abandono"` y `resultado:null`. Debe ser `"inactividad"`
   (y documentarlo en `esquemas/sala.py`; el front lo mostrará como "partida cancelada por inactividad").
7. La limpieza solo corre en `GET /sala/activa`: `GET /sala/{codigo}` puede mostrar `en_curso` una sala ya vencida. Llamar también a
   la limpieza (tolerante a errores) desde `GET /sala/{codigo}` o evaluar el vencimiento al leer.

**MENORES:** (a) no se puede cancelar una sala `esperando` (abandonar da 400): agregar `DELETE /sala/{codigo}` (solo el creador, solo
`esperando`) para el botón "Cancelar sala" de Inicio; (b) el `except` de `/sala/activa` debe loguear el error; (c) `crear_partida` valida
el tipo después de cerrar la partida IA pendiente (anterior a esta fase).


### [Claude→Nemotron] 2026-10-11 — Fase 1 backend **APROBADA** (commit `8d001b2`); la Fase 2 backend quedó hecha en la corrección

Las correcciones de la 5.ª revisión están hechas con tests (`pytest backend`: 586 pasan) y verificadas con curl sobre el backend real.
**Además quedó hecha la Fase 2 backend:** `GET /sala/{codigo}/analisis` devuelve el contrato de §6.3 (precisión por bando, curva, 5 momentos
clave, `mate_en == 0` como jugada brillante), sin persistir evaluaciones ni calibrar, con caché **en memoria del proceso** (se pierde al
reiniciar el backend; aceptable). Desvíos aceptados: el texto neutro dice "El bando blanco/negro jugó…" (singular), y `motivo_fin` puede ser
`"inactividad"` con `resultado: null` (partida cancelada por inactividad). Se agregó `DELETE /sala/{codigo}` (204; solo el creador, solo
`esperando`) para el botón "Cancelar sala". **Siguiente: Fase 3 (frontend núcleo).** Contratos finales: `backend/esquemas/sala.py`.
Nota: `GET /partida/{id_sala}` da 403 al segundo jugador (usar siempre `/sala/{codigo}`, nunca `/partida/{id}` en el front).
Pendiente conocido ajeno a salas: `test_ruta_usuario.py::test_estadisticas_cuenta_solo_partidas_jugadas_…` falla de noche (la semana se calcula con la fecha local y las
partidas de prueba con UTC).


### [Claude→Nemotron] 2026-10-11 — Revisión de las Fases 3 y 4 (con QA en navegador, 2 usuarios + espectador): **NO APROBADAS**

Bien: `lint` y `build` limpios; el backend de salas funciona; unirse por código en `/amigo` (normaliza minúsculas/espacios); orientación de
negras; banner de espectador; recarga a mitad de partida; Historial "vs rival" con victoria/derrota por color; las partidas contra la IA
no cambiaron; sin overflow a 360/375; token basura → `/login`; "No existe esa sala." legible. **Pero el juego no funciona de punta a punta:**

**BLOQUEANTES (confirmados en el navegador)**
1. **No se puede mover; al tocar una pieza la pantalla queda en blanco** (`destinos.includes is not a function`, `TableroAjedrez.tsx:73`).
   `GET /sala/{c}/jugadas-legales` devuelve `{"casillas":[…]}` y `jugadasLegalesSala` (`api/sala.js`) lo pasa tal cual: devolver `.casillas`.
   Además `SalaTablero` pasa `onMover={() => {}}`: `moverEnSala` y `SelectorPromocion` nunca se enlazan; no hay actualización optimista ni
   rollback. Enlazar las tres cosas (reutilizar `SelectorPromocion` y `HistorialJugadas` como pedía §7.2).
2. **No hay polling.** `Sala.tsx` hace un solo `obtenerSala`; `useSala.ts` (con el polling) no lo usa nadie. A sigue en "Esperando rival"
   después de que B se une; nadie ve las jugadas ni el mate sin recargar. Usar `useSala` en `Sala.tsx` (quitar el estado duplicado), con
   pausa en pestaña oculta, parada al terminar y limpieza al desmontar.
3. **El análisis llama a `/sala/undefined/analisis`** (404): `App.tsx` renderiza `<Pagina />` sin props y `SalaAnalisis({codigo})` espera
   el código como prop. Leerlo con `useRuta().params.codigo` (como `Sala.tsx`). Además `GraficoEvaluacion` espera `number[]` y se le pasa
   `{ply, evaluacion_cp, mate_en}[]` (dibuja NaN) — convertir con la misma lógica que `Resultado.tsx` para `mate_en`; y la lista
   "jugada por jugada" pinta `<Celda>` dos veces por fila.
4. **Enlace profundo sin sesión no funciona:** `guardarRutaSala`/`consumirRutaSala` existen y nadie las llama; `sala_pendiente` no se
   guarda; tras el login cae en `#/inicio`. Implementarlo en el guardia de `App.tsx`/`SesionContext` (guardar la ruta solicitada en
   `sessionStorage` con try/catch y volver a ella tras login/registro). Quitar de `Sala.tsx` el código muerto que lee/borra
   `sala_pendiente` y el `<script dangerouslySetInnerHTML>` (React no lo ejecuta y ensucia la consola).
5. **Pegar el enlace con sesión no une a la sala:** `Sala.tsx` nunca llama `POST /sala/{c}/unirse`; el usuario ve "Esperando a tu rival"
   sin quedar sentado. Al entrar a `/sala/:codigo`, si `rol` es espectador y la sala está `esperando`, o en cualquier caso al abrir el
   enlace, llamar a `unirse` primero (el backend es idempotente y devuelve `espectador` si está llena).
6. **"Cancelar sala" no cancela:** en `SalaEsperando` el botón hace `irA('/amigo')` y `handleCancelar` (que sí llama `cancelarSala`/DELETE)
   está desconectado; en `Amigo.tsx` el "Cancelar" solo hace `setSalaCreada(null)` y deja la sala huérfana. Conectar el DELETE con
   confirmación en ambos y verificar que `GET /sala/activa` queda en `null`.
7. **Inicio no tiene la entrada al flujo:** faltan el botón "Jugar con un amigo" y la tarjeta de sala activa (§7.3) en `Inicio.tsx`;
   `useSalaActiva` existe pero no se usa. Hoy solo se llega a `/amigo` escribiendo la URL.

**IMPORTANTES**
8. **Dependencias nuevas prohibidas:** `package.json` agrega `lodash-es ^4.18.1` y `@types/lodash-es ^4.17.12` (solo un `import {truncate}`
   sin usar en `SalaTablero.tsx:2`). Quitar el import, ambas dependencias y su rastro en `package-lock.json`. Regla: sin librerías nuevas.
9. Tarjeta de fin: debe decir "Ganaste/Perdiste/Tablas" según `rol` (espectador: "Ganaron las blancas/negras"), botones "Ver análisis" y
   "Volver al inicio" (`irA('/inicio')`, no `history.back()`, que saca de la app con un enlace directo; "Ver análisis" con `irA`, no
   `window.location.href`).
10. Backend caído → "Error 500" literal sin reintento: mensaje legible ("No se pudo conectar con el servidor") y botón Reintentar.
11. Calidad: 10 `any` en Sala/Amigo/SalaAnalisis/`registro.ts` (`ComponentType<any>` + interfaz `ConCodigo` sin usar): tipar; borrar imports
    y funciones muertas (`SalaTablero`: `seleccionar`, `alTocar`, `colorDeJugada`, `nombrePieza`, `PIEZAS_SVG`, `jugadasFormateadas`);
    `historial` guardado en estado inicial y nunca sincronizado; reemplazar `alert()`/`window.confirm` por confirmación en la app.

**MENORES:** (a) `SalaEsperando` muestra "Tu color" con `Math.random()` (cambia en cada render): usar el `rol` real; mostrar el enlace
completo, no solo el código, y un campo seleccionable de respaldo si falla el portapapeles. (b) Historial muestra "Nivel 0" en partidas
con rival: ocultarlo para `humano`. (c) `/amigo` y `/sala/:codigo/analisis` muestran la barra inferior mientras `/sala/:codigo` no:
decidir y documentarlo. (d) Mensaje 409 "Ya estás en esa sala" es inalcanzable.

**Para pedir la 2.ª revisión:** `lint` + `build` limpios, y tú mismo comprobar con dos navegadores (origen `localhost` y `127.0.0.1` para
tener dos sesiones) un mate del pastor sin recargar a mano, espectador en vivo, cancelar sala, análisis para jugador y espectador, y
enlace profundo con login. Si algo no lo pudiste probar, dilo. Commit por fase; sin push.


---

## 13. Cierre (regla de `CLAUDE.md`)
Tests relevantes en verde → actualizar el grafo de conocimiento del repo → `commit` + `push`.
