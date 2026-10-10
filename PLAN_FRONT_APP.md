# PLAN_FRONT_APP.md — Plan de implementación de `front_app/`

Plan para construir `front_app/`: la **funcionalidad del rol jugador de la web** (`frontend/`)
con el **diseño de la app móvil** (`app_movil/`), usando la **misma tecnología que el frontend
web**. Lo implementan dos agentes en paralelo (Claude y Nemotron), por eso el plan reparte el
trabajo en bloques con archivos disjuntos y contratos fijos.

> Prioridad (ver `CLAUDE.md`): lo que se pueda demostrar funcionando antes que lo elegante.
> Al terminar cada fase debe quedar algo que corra de punta a punta contra el backend real.

---

## 1. Objetivo y alcance

**Qué es:** una web mobile-first, solo para cuentas con rol `jugador`, que consume el mismo
backend FastAPI (`backend/`) que `frontend/` y `app_movil/`. No tiene datos simulados propios.

**Dentro del alcance (funciones del jugador, ya existentes en la web):**

| Función | Pantalla web de referencia | Pantalla móvil de referencia (diseño) |
|---|---|---|
| Login / registro (siempre rol jugador) | `paginas/Login` | `login_screen.dart` |
| Onboarding de piezas (HU12) | `paginas/Onboarding` | `learning/*` |
| Test de nivel (HU13) | `Onboarding` / `PanelAprendizaje/TuNivel` | `evaluation_result_screen.dart` |
| Home: saludo, nivel, racha, estadísticas, mapa de habilidades (HU14) | `PanelAprendizaje` | `home_screen.dart` |
| Elegir oponente y nivel (HU10) | `SalaControl` (configuración) | `mode_selection_screen.dart`, `config_screen.dart` |
| Jugar: tablero, jugadas legales, reloj, barra de evaluación (HU6) | `SalaControl` | `game_screen.dart` |
| Fin de partida y análisis (HU5) | `SalaControl` / `RegistroPartidas` | `victory_screen.dart`, `defeat_screen.dart` |
| Panel de aprendizaje: camino, piezas, repaso, tutor (chat Turing) | `PanelAprendizaje`, `ChatTuring`, `Aprendizaje` | `learning/*` |
| Historial de partidas propias | `RegistroPartidas` | (pestaña en Home) |
| Perfil (nombre, foto, edad, bio) | `Perfil` | pestaña Perfil de `home_screen.dart` |
| Ver la demostración en vivo del facilitador (solo lectura) | `DemostracionEnVivo` | — (nueva en móvil) |

**Fuera del alcance (no hacer sin que se pida):**
- Todo lo del facilitador: Sala de Control como tal, Razonamiento Neuronal, Monitoreo,
  Configuración de Enseñanza, Entrenamiento del Modelo, Administración, permisos por partida.
- Simulación 3D del brazo y cámara del tablero físico: quedan **fuera de la primera entrega**.
  Solo se mostrarían si el facilitador activa el permiso de esa partida (ver §9, fase 5 opcional).
- Aprendizaje en vivo, multijugador, ranking, brazo físico real (reglas de `CLAUDE.md`).
- Modo oscuro (la app móvil solo tiene tema claro).

---

## 2. Decisiones técnicas

**Stack (idéntico a `frontend/`, mismas versiones, fijadas exactas en `package.json`):**
Vite 6 · React 19 · TypeScript 5.8 · Tailwind CSS 4 (`@tailwindcss/vite`) · `lucide-react` ·
`motion` · `gsap` + `@gsap/react` (solo si hace falta animar) · `three` NO (no hay 3D en la
primera entrega).

**Decisiones tomadas (opción más simple, sin dependencias nuevas):**

1. **Carpeta `front_app/` en la raíz del repo**, hermana de `frontend/`, como carpeta normal del
   repo principal. **No** es submódulo y **no** va dentro de `frontend/` (que sí es submódulo
   con su propio remoto).
2. **Sin router externo.** La web usa estado (`pantallaActiva`) y no `react-router`; en
   `front_app/` se usa un mini-router propio por `location.hash` (`#/home`, `#/juego`, …) en
   `src/router.ts`. Así el botón "atrás" del navegador funciona sin agregar una librería.
3. **Capa de API reutilizada por copia, no por enlace simbólico.** Se copian
   `frontend/src/api/backend.js`, `ajedrez.js`, `nivelJugador.js`, `aprendizaje.js`,
   `formatoTiempo.js` y `contenido/piezas.js` a `front_app/src/` y se mantienen como módulos
   aparte (`src/api/`, `src/dominio/`). Motivo: `frontend/` es un submódulo con otro ciclo de
   commits; un symlink rompe el build y el deploy. Se anota en cada archivo copiado de dónde
   viene. Los endpoints que falten en `backend.js` (p. ej. `GET /usuario/estadisticas`, hoy no
   exportado ahí) se agregan en `front_app/src/api/`, sin tocar el original.
4. **Diseño = tokens de la app móvil**, traducidos a variables de Tailwind 4 (`@theme` en
   `src/index.css`) desde `app_movil/lib/theme/app_colors.dart`,
   `app_text_styles.dart` y `DESIGN (1).md` (sistema "Neural Grandmaster"):
   - Primario `#087F5B`, acento neural `#00DAF3`, ámbar `#F59E0B`, error `#BA1A1A`.
   - Fondo `#F8FAFC`, superficies `#EFF4FF` → `#D3E4FE`, texto `#0F172A`.
   - Calidad de jugada: brillante `#00DAF3`, mejor `#087F5B`, error `#F59E0B`, blunder `#EF4444`.
   - Tablero: casilla clara `#FFFDFD`, oscura `#B8D0EB`, resaltado `#087F5B` al 50 %,
     última jugada `#00DAF3` al 50 %, jaque `#EF4444` al 80 %.
   - Tipografías: **Space Grotesk** (títulos) y **Plus Jakarta Sans** (cuerpo) por Google Fonts.
   - Componentes: tarjetas "glass" (`GlassCard`), esquinas muy redondeadas, mucho aire.
5. **Layout mobile-first:** pensado para 360–430 px; en escritorio se centra en una columna de
   ~480 px (marco tipo teléfono) para que se vea igual que la app. Navegación inferior de 4
   pestañas: **Inicio · Jugar · Aprender · Perfil**.
6. **Autenticación:** igual que la app móvil. `login` manda `rol_esperado: "jugador"`; una cuenta
   facilitador recibe 403 y no entra. Registro crea siempre jugador (sin clave de facilitador).
   JWT en `localStorage` (envuelto en try/catch); al abrir se valida con `GET /auth/me`.
   Cualquier ruta sin sesión redirige a `#/login`.
7. **Puerto de desarrollo `5174`** (la web usa `5173`), con el mismo proxy hacia
   `http://127.0.0.1:8000` que `frontend/vite.config.ts` (`/jugada`, `/analisis`, `/partida`,
   `/vision`, `/health`, `/aprendizaje`, `/auth`, `/simulacion`, `/usuario`, `/media`,
   `/tutor`, …; omitir `/facilitador` y `/entrenamiento`).
8. **Modelo y motor:** nada cambia en el backend. Si el jugador elige `tipo_oponente = "modelo"`,
   decide el modelo propio sin consultar a Stockfish; con `"motor"` decide Stockfish (regla 1 de
   `CLAUDE.md`). El front solo manda el tipo y muestra lo que devuelve el backend.

---

## 3. Estructura de carpetas

```
front_app/
├── index.html
├── package.json            # versiones exactas, mismas que frontend/
├── tsconfig.json
├── vite.config.ts          # puerto 5174 + proxy
├── README.md               # cómo levantar (backend + front_app)
├── public/                 # logo, imágenes (de imgapp/)
└── src/
    ├── main.tsx
    ├── App.tsx             # layout (marco móvil + nav inferior) y render por ruta
    ├── router.ts           # mini-router por hash
    ├── index.css           # @theme con tokens de la app móvil + fuentes
    ├── api/
    │   ├── backend.js      # copia de frontend/src/api/backend.js
    │   └── extra.js        # endpoints que falten (estadísticas, etc.)
    ├── dominio/            # ajedrez.js, nivelJugador.js, aprendizaje.js, formatoTiempo.js, piezas.js
    ├── estado/
    │   └── SesionContext.tsx   # usuario, token, estadísticas, cargarEstadisticas()
    ├── componentes/        # ver §5 (UI compartida)
    └── paginas/
        ├── Login/
        ├── Onboarding/
        ├── Inicio/
        ├── Jugar/          # selección de modo, configuración, partida, resultado
        ├── Aprender/       # camino, piezas, tablero, filas/columnas, posición inicial, tutor
        ├── Historial/
        ├── Perfil/
        └── Demostracion/
```

Se agrega a `.gitignore`: `front_app/node_modules`, `front_app/dist`.

---

## 4. Contrato entre los dos agentes (para no pisarse)

Dos agentes trabajan a la vez. Reglas:

1. **Una carpeta = un dueño.** Nadie edita archivos del otro bloque; si hace falta un cambio,
   se deja anotado en la sección "Pedidos entre bloques" al final de este archivo.
2. **El Bloque A (Claude) publica primero la base** (Fase 0 y 1: scaffold, tema, componentes
   compartidos, router, sesión). El Bloque B (Nemotron) no empieza pantallas hasta que la Fase 1
   esté commiteada, salvo trabajo que no dependa de ella (ver Fase 1B).
3. **Interfaz de una pantalla:** cada página exporta un componente por defecto sin props
   obligatorias, y obtiene sesión y navegación solo de `useSesion()` y `irA(ruta)`:
   ```ts
   // estado/SesionContext.tsx
   useSesion(): { usuario, estadisticas, cargarEstadisticas(), cerrarSesion() }
   // router.ts
   irA(ruta: string, params?: Record<string,string>): void
   useRuta(): { ruta: string, params: Record<string,string> }
   ```
4. **Rutas fijas** (las define A en `router.ts`; B solo las usa):
   `/login`, `/onboarding`, `/inicio`, `/jugar`, `/jugar/config`, `/jugar/partida/:id`,
   `/jugar/resultado/:id`, `/aprender`, `/aprender/piezas`, `/aprender/tablero`,
   `/aprender/filas-columnas`, `/aprender/posicion-inicial`, `/aprender/tutor`,
   `/historial`, `/perfil`, `/demostracion`.
5. **UI compartida solo en `componentes/`** y solo la edita A. B la consume. Si B necesita un
   componente nuevo reutilizable, lo crea dentro de su propia página y se promueve después.
6. **Estilos solo con tokens** de Tailwind (`bg-primary`, `text-on-surface`, …). Prohibido
   `#hex` suelto en pantallas (en la app móvil hay 68 `Color(0x…)` sueltos: no repetir el error).
7. **Archivos de máximo ~400 líneas.** Dividir antes de pasar de ahí (la app móvil tiene
   archivos de 800–1300 líneas y es una de sus debilidades).
8. **Commits:** mensajes simples describiendo el cambio, sin mencionar IA, herramientas ni
   asistentes, sin `Co-Authored-By`; el autor es quien usa la sesión (regla obligatoria de
   `CLAUDE.md`). Commits chicos por pantalla/componente, con prefijo `feat(front_app):`.
9. **Sin librerías nuevas** sin consultar. Si una fase parece necesitar una, se anota en §10.

---

## 5. Componentes compartidos (Bloque A, Fase 1)

Réplica web de los widgets de `app_movil/lib/widgets/`:

| Componente web | Equivale en la app móvil | Notas |
|---|---|---|
| `GlassCard` | `glass_card.dart` | Tarjeta translúcida, borde `surfaceGlassBorder` |
| `TableroAjedrez` | `chess_board.dart` | Tablero interactivo: jugadas legales, última jugada, jaque; orientación; toque para mover |
| `TableroDemo` | tablero de `learning/*` | Solo lectura, con puntos de movimientos legales ilustrativos |
| `BarraEvaluacion` | `evaluation_bar.dart` | Ventaja blancas/negras, animada |
| `RelojAjedrez` | `chess_clock.dart` | Estado activo y poco tiempo (ámbar) |
| `HistorialJugadas` | `move_history.dart` | Lista SAN con badge de calidad |
| `GraficoEvaluacion` | `evaluation_history_chart.dart` | Curva de la partida (SVG propio, sin librería de gráficos) |
| `RadarHabilidades` | radar del Home | SVG propio, 5 ejes |
| `NavInferior` | pestañas de `home_screen.dart` | Inicio · Jugar · Aprender · Perfil |
| `BotonPrimario`, `Chip`, `ProgresoBarra`, `Cargando`, `ErrorReintentar` | varios | Estados de carga y error consistentes |

Las piezas del tablero reutilizan el set que ya usa la web (`PiezaModelo3D` NO; usar imágenes o
SVG/Unicode como en `TableroSoloLectura.jsx`).

---

## 6. Reparto de trabajo

### Bloque A — Claude (base + flujo central de partida)
Scaffold, tema, componentes compartidos, router, sesión, **Login**, **Inicio**, y todo
**Jugar** (selección de modo → configuración → partida → resultado). Es el camino crítico y el
más delicado porque toca el tablero y el análisis.

### Bloque B — Nemotron (aprendizaje y perfil)
**Onboarding**, **Aprender** (camino, piezas, tablero, filas/columnas, posición inicial,
**chat tutor Turing**), **Historial**, **Perfil**, **Demostración** (solo lectura).
Son pantallas casi independientes del tablero interactivo, lo que permite avanzar en paralelo.

---

## 7. Fases

Cada fase termina con: `npm run lint` (tsc) sin errores, `npm run build` ok, y prueba manual
contra el backend real. Marcar `[x]` aquí al completar.

### Fase 0 — Scaffold (A) · ~medio día
- [x] Crear `front_app/` con `package.json` (versiones exactas de `frontend/`), `tsconfig`,
      `vite.config.ts` (5174 + proxy), `index.html`, `main.tsx`.
- [x] `index.css` con `@theme` (tokens de §2.4) y carga de Space Grotesk / Plus Jakarta Sans.
- [x] `.gitignore` y `README.md`.
- **Listo cuando:** `npm run dev` abre una pantalla con el fondo y la tipografía correctos.

### Fase 1 — Base compartida (A) · ~1 día
- [x] `router.ts` (hash) y rutas de §4.
- [x] Copiar capa de API y dominio (§2.3); `api/extra.js` con `GET /usuario/estadisticas`.
- [x] `SesionContext` (login, restauración con `/auth/me`, cerrar sesión, estadísticas).
- [x] `App.tsx`: marco móvil centrado + `NavInferior` + guardia de sesión.
- [x] Componentes de §5 (al menos `GlassCard`, `BotonPrimario`, `NavInferior`, `Cargando`,
      `ErrorReintentar`, `TableroAjedrez`, `TableroDemo`).
- **Listo cuando:** se puede navegar entre rutas vacías y la guardia redirige a `#/login`.
- **Fase 1B (B, en paralelo, sin depender de A):** copiar `contenido/piezas.js` y
  `aprendizaje.js`, y redactar en `paginas/Aprender/datos.ts` el contenido de las 8 tarjetas de
  piezas y de las pantallas de tablero/filas-columnas/posición inicial.

### Fase 2 — Entrada y home (A) · ~1 día
- [x] **Login/registro** (diseño de `login_screen.dart`; `rol_esperado: "jugador"`; error 403
      con mensaje claro; login con Google solo si `GOOGLE_CLIENT_ID` está configurado).
- [x] **Inicio** (diseño de `imgapp/home.png`): saludo, nivel, racha, tarjeta "Jugar",
      3 estadísticas, `RadarHabilidades`, progreso al siguiente nivel, frase del día. Todo desde
      `GET /usuario/estadisticas` y `/auth/nivel`; sin números inventados (si falta un dato se
      muestra "—").
- **Listo cuando:** registrar un jugador nuevo, entrar y ver su Home con datos reales.

### Fase 3 — Jugar (A) · ~2 días
- [x] **Selección de modo** y **configuración** (oponente `motor`/`modelo`, nivel precargado del
      perfil, color; `POST /partida`).
- [x] **Partida**: `TableroAjedrez` con jugadas legales (`/partida/:id/jugadas-legales`) y mover
      (`/partida/:id/mover`), reloj, historial, `BarraEvaluacion` y calidad de la jugada
      (pendientes de HU6 en `docs/plan_sprints.md`: mostrar lo que el backend ya devuelva,
      sin inventar), retomar partida en curso (`obtenerPartidaEnCurso`), rendirse/terminar.
- [x] **Resultado** (victoria/derrota, `imgapp/derrota.png`): análisis completo
      (`analisis-completo`), curva de evaluación, lista de errores con explicación, botón
      "Jugar de nuevo". Dispara `calibrarPartida` y refresca nivel/estadísticas.
- **Listo cuando:** se juega una partida completa contra el motor y contra el modelo, y el
  resultado y las estadísticas del Home se actualizan.

### Fase 4 — Aprender, historial, perfil (B) · ~2 días (en paralelo con las fases 2–3 de A)
- [ ] **Onboarding** + **test de nivel** (`guardarNivelEstimado`), con el diseño de
      `imgapp/mide tu nivel.png` y `resultado de tu evaluacion.png`.
- [ ] **Aprender**: camino de aprendizaje, tarjetas de piezas con `TableroDemo` y movimientos
      legales (diseño de `imgapp/targetas de aprendizaje.png`), tablero, filas/columnas,
      posición inicial; progreso persistido como lo hace la web.
- [ ] **Tutor Turing**: chat (`enviarMensajeTutor`, `obtenerHistorialTutor`,
      `borrarHistorialTutor`), narración por voz con Web Speech API (sin dependencia nueva).
- [ ] **Historial** (`historialPartidasPropio`, paginado) con acceso al análisis de cada partida.
- [ ] **Perfil** (`obtenerPerfil`, `actualizarPerfil`, `subirFotoPerfil`) y botón cerrar sesión.
- [ ] **Demostración en vivo** (`obtenerDemostracionActiva`, sondeo cada ~2.5 s, tablero de solo
      lectura, banner en Inicio cuando haya una activa).
- **Listo cuando:** un jugador nuevo completa onboarding → test de nivel → una tarjeta de
  pieza → conversa con el tutor → edita su perfil, todo contra el backend real.

### Fase 5 — Integración y cierre (A + B) · ~1 día
- [ ] Revisión cruzada: A revisa el código de B y viceversa (rutas, tokens, tamaño de archivos).
- [ ] Pasada de diseño contra las capturas de `imgapp/` y contra `app_movil/` (espaciados,
      tipografía, estados de carga/vacío/error en cada pantalla).
- [ ] Pasada responsive: 360, 390, 430 px y escritorio (marco centrado).
- [ ] **QA de punta a punta** con el subagente `qa-reviewer` (modo SYSTEM): backend real,
      registro → onboarding → partida → resultado → historial → perfil, y cuenta facilitador
      rechazada con 403.
- [ ] Actualizar `docs/plan_sprints.md` (qué quedó hecho en `front_app/`) y `README.md`.
- [ ] (Opcional) simulación 3D / cámara, solo si el facilitador activa el permiso de la
      partida (`PATCH /partida/{id}/permisos`); reutilizar `SimuladorBrazoTablero3D`. Requiere
      sumar `three`, que ya está en el stack web.
- **Listo cuando:** demo completa sin errores en consola y `npm run build` limpio.

---

## 8. Cómo se prueba

- **Estático:** `npm run lint` (`tsc --noEmit`) y `npm run build` en cada commit.
- **Manual contra backend real** (no mocks), usando las cuentas de `docs/usuarios_locales_dev.md`
  (`jugador@test.com`):
  ```bash
  # terminal 1 — backend
  DATABASE_URL=sqlite:///./test.db uvicorn backend.main:app --reload
  # terminal 2 — front_app
  cd front_app && npm install && npm run dev      # http://localhost:5174
  ```
  Recordatorio de entorno local (memoria del proyecto): el backend corre también en Docker en
  `:8000`; y `torch` necesita `KMP_DUPLICATE_LIB_OK=TRUE` si el backend se levanta a mano.
- **Verificación visual:** comparar cada pantalla con su captura en `imgapp/` y con la app móvil.
- **Tests unitarios:** no hay framework de pruebas en `frontend/`. Para la lógica pura
  (`dominio/*`) se propone **Vitest** — requiere aprobación (ver §10). Sin aprobación, la
  verificación queda en lint + build + QA manual.

---

## 9. Riesgos y cómo se cubren

| Riesgo | Mitigación |
|---|---|
| Dos agentes pisándose archivos | Dueño único por carpeta (§4) y fase 1 publicada antes de que B empiece pantallas |
| Divergencia de `backend.js` copiado vs. el de la web | Archivo marcado como copia; cambios de contrato del backend se aplican en ambos |
| Pantalla de juego sin todo el feedback de HU6 | Mostrar solo lo que ya devuelve el backend; lo faltante queda anotado, no inventado |
| `Tablero` táctil impreciso en celular | Mover por toque en dos pasos (origen → destino) como la app, no por arrastre |
| Archivos gigantes (como `SalaControl.jsx` de 1860 líneas) | Límite de ~400 líneas por archivo |
| CORS / red desde celular físico | Proxy de Vite; para probar en celular, `vite --host` y misma Wi-Fi |
| iCloud (el repo está en Escritorio) afecta builds | `node_modules` y `dist` quedan ignorados; si falla el build, mover `dist` fuera de iCloud |

---

## 10. Decisiones abiertas (responder antes de la Fase 1)

1. ¿Aprobás **Vitest** como devDependency para probar `dominio/*`? (Por defecto: no.)
2. ¿Nombre de carpeta final **`front_app/`** (con guion bajo, como `app_movil/`)? (Por defecto: sí.)
3. ¿Incluir en esta entrega la **simulación 3D / cámara** (Fase 5 opcional)? (Por defecto: no.)
4. ¿Login con Google en `front_app/`, o solo email y contraseña? (Por defecto: solo email.)
5. ¿Deploy: `front_app/` se agrega a `deploy/docker-compose.yml` como un servicio más, o por ahora
   solo corre en local? (Por defecto: solo local.)

---

## 11. Pedidos entre bloques

*(Vacío. Cada agente anota aquí lo que necesita del otro: `[A→B]` o `[B→A]`, fecha, qué se pide,
estado.)*

- `[A→backend]` 2026-10-10: `POST /partida` no acepta color (el jugador siempre juega blancas) ni hay endpoint
  para rendirse; `retroalimentacion_en_vivo.calidad` siempre es `"buena"` (la UI muestra solo la probabilidad de
  victoria); `analisis-completo` marca como `blunder` la jugada que da mate (`mate_en: 0`) y da precisión 0 %; no hay
  desglose de habilidades por fase (el radar del Inicio usa 5 métricas reales). La imagen Docker de :8000 estaba
  desactualizada (sin `/auth/nivel` ni `/partida/en-curso`): reconstruirla.

---

## 12. Checklist de cierre (regla de `CLAUDE.md`)

Antes de dar `front_app/` por terminada: tests/lint/build ok → actualizar el grafo de
conocimiento del repo → `commit` + `push` (sin mencionar IA en ningún mensaje ni archivo).
