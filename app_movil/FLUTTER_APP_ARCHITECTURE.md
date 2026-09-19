# ChessIA Flutter App — Estructura y Lógica

> Documentación técnica de la app móvil (Flutter 3.x, Dart 3.x)  
> Ubicación: `/app_movil`

---

## 1. Visión General

| Aspecto | Detalle |
|---------|---------|
| **Framework** | Flutter 3.x (Material 3) |
| **Arquitectura** | Provider + GoRouter (State management + Routing) |
| **Backend** | FastAPI (FastAPI + JWT + SQLite/PostgreSQL) |
| **Auth** | Email/Password (bcrypt + JWT access/refresh tokens) |
| **Tema** | Design System "Neural Grandmaster" (Emerald, Cyan, Amber, Slate, Glassmorphism) |
| **Plataformas** | Android, iOS, Web (single codebase) |

---

## 2. Estructura de Carpetas

```
app_movil/
├── pubspec.yaml                 # Dependencias + fonts declaration
├── assets/
│   ├── fonts/                   # Space Grotesk, Plus Jakarta Sans, JetBrains Mono
│   └── images/                  # Placeholders para logos, ilustraciones
├── lib/
│   ├── main.dart                # Entry point + GoRouter + Providers
│   ├── models.dart              # Enums compartidos (OpponentType, MoveQuality)
│   ├── models/
│   │   └── learning/
│   │       └── learning_models.dart  # Entidades pure Dart del módulo Aprender
│   ├── theme.dart               # Barrel export del Design System
│   ├── theme/
│   │   ├── app_colors.dart      # Paleta completa (semántica, no solo valores)
│   │   ├── app_text_styles.dart # 13 estilos tipográficos (3 fuentes)
│   │   ├── app_spacing.dart     # Espaciado 4px/8px, radius, gutters
│   │   ├── app_shadows.dart     # 4 niveles elevation + neural glows + glass
│   │   └── app_theme.dart       # ThemeData M3 + extensiones Chess/Glass
│   ├── services/
│   │   ├── services.dart        # Barrel export
│   │   ├── api_config.dart      # Config base URL del backend
│   │   ├── auth_api_service.dart      # Cliente HTTP (Dio) + FlutterSecureStorage + Interceptors
│   │   ├── auth_service.dart         # Servicio helper de auth
│   │   ├── auth_wrapper.dart         # Wrapper del AuthProvider
│   │   ├── auth_provider.dart        # Provider global (AuthProvider) — BACKEND REAL
│   │   ├── chess_api.dart            # API partidas, análisis, motor
│   │   ├── partida.dart              # Modelos Partida, Analisis, etc.
│   │   ├── local_auth_*.dart         # Auth local — LEGACY (no usar)
│   │   └── learning/
│   │       ├── learning_service.dart          # Catálogo + reglas de negocio del camino
│   │       └── learning_path_controller.dart  # Estado reactivo (ChangeNotifier)
│   ├── widgets/
│   │   ├── widgets.dart         # Barrel export
│   │   ├── brand_logo.dart      # Logo/identidad en pantallas
│   │   ├── evaluation_bar.dart  # Barra eval horizontal/vertical (JetBrains Mono badge)
│   │   ├── chess_clock.dart     # Relojes pill + pulse dot + low-time amber
│   │   ├── move_history.dart    # Chips horizontales con quality dots
│   │   ├── glass_card.dart      # GlassCard, GlassHUD, TacticalCard, TelemetryPill
│   │   ├── chess_board.dart     # Tablero 8x8 (GridView + coordenadas)
│   │   ├── turn_status_card.dart, evaluation_round_progress.dart, evaluation_history_chart.dart
│   │   ├── learning_widgets.dart  # Base UI de lecciones de aprendizaje
│   │   └── learning/             # Widgets del "Camino de Maestría"
│   │       ├── chapter_symbol.dart   # ChapterSymbol → IconData/glifo
│   │       ├── chapter_node.dart     # Nodo circular + ActiveChapterCard
│   │       ├── path_connector.dart   # Curvas del péndulo S (pathSideOffset = 40)
│   │       ├── path_header.dart      # LearningPathHeader + StreakBadge
│   │       ├── path_progress_card.dart # Nivel/XP/barra de progreso
│   │       ├── path_unit_banner.dart # Banner de la unidad en curso
│   │       └── learning_path.dart    # Orquestador del camino + partículas
│   └── screens/
│       ├── screens.dart         # Barrel export
│       ├── login_screen.dart    # Login/Register email+password
│       ├── mode_selection_screen.dart # "¿Qué quieres hacer hoy?" + diagnóstico por rondas
│       ├── config_screen.dart   # Selector oponente + slider nivel 1-20
│       ├── game_screen.dart     # Tablero + clocks + eval bar + análisis panel
│       ├── evaluation_result_screen.dart # Trofeo animado + rank + métricas
│       ├── home_screen.dart     # Dashboard (stats, radar chart, skills, actions)
│       ├── victory_screen.dart  # Trofeo dorado + chart evolución + confeti
│       ├── defeat_screen.dart   # Reyes ilustración + chart caída + advice
│       └── learning/
│           ├── learning_path_screen.dart     # Camino de Maestría (/learning-path)
│           ├── board_basics_screen.dart      # Lección (routeName en clase)
│           ├── pieces_screen.dart
│           ├── ranks_files_screen.dart
│           └── initial_position_screen.dart
```

Barrels: `widgets.dart`, `screens.dart` re-exportan todos los widgets/pantallas
(incluidos los de `learning/`).

---

## 3. Flujo de Navegación (GoRouter)

```
Rutas públicas (`_rutasPublicas = {/splash, /login}`):
  /splash         → Splash (mientras `isInitializing`; con sesión salta a /home)
  /login          → LoginScreen

Rutas autenticadas (redirect en GoRouter):
  /mode-selection → ModeSelectionScreen (diagnóstico por rondas / test rápido)
  /config         → ConfigScreen (recibe diagnosticLevel como extra)
  /game           → GameScreen (partidaId, opponent, level, enableFeedback,
                                esDiagnostico, diagnosticoRonda, diagnosticoPrecisiones)
  /evaluation-result → EvaluationResultScreen (level, rank, accuracy, gamesPlayed)
  /home           → HomeScreen (BottomNav: Home, Stats, Progress, Profile)
  /victory        → VictoryScreen (playerName, accuracy, moves, finalEval, opponent)
  /defeat         → DefeatScreen (playerName, accuracy, moves, finalEval, opponent)

Rutas de aprendizaje (HU12):
  /learning-path          → LearningPathScreen ("Camino de Maestría")
  /learning/board-basics  → BoardBasicsScreen
  /learning/pieces        → PiecesScreen
  /learning/ranks-files   → RanksFilesScreen
  /learning/initial-position → InitialPositionScreen

Redirect logic:
  - Si isInitializing → /splash (mantiene el splash mientras arranca auth)
  - Si !loggedIn && destino != /login → /login
  - Si loggedIn && destino ∈ {/splash, /login} → /home
  - Sino → null (deja navegar)
```

---

## 4. Gestión de Estado (Provider)

### Providers principales (en `main.dart`):
```dart
ChangeNotifierProvider(create: (_) => AuthProvider())  // Auth global
```

### AuthProvider (`lib/services/auth_provider.dart`):
- **Estado**: `user` (AppUser?), `isLoading`, `error`
- **Métodos**: `login()`, `register()`, `logout()`, `clearError()`
- **Persistencia**: `FlutterSecureStorage` (access_token, refresh_token, user)
- **Auto-refresh**: Interceptor en Dio renueva access_token con refresh_token automáticamente

### Flujo de auth:
```
App start → AuthProvider._checkAuthState()
  → hasValidToken? → GET /auth/me → set user
  → NO token → muestra /login

Login/Register → POST /auth/login|registro
  → guarda tokens en SecureStorage
  → set user → navega a /onboarding
```

---

## 5. Design System ("Neural Grandmaster")

### Colores semánticos (`app_colors.dart`):
| Rol | Hex | Uso |
|-----|-----|-----|
| Primary Emerald | `#087F5B` | Acciones primarias, jugadas correctas, win%+ |
| Secondary Cyan | `#00DAF3` | Motor IA, análisis neural, best-move |
| Tertiary Amber | `#F59E0B` | Alertas tiempo, blunders, streaks |
| Surface-0 | `#F8FAFC` | Canvas base |
| Surface-1 | `#FFFFFF` | Cards elevadas |
| Surface-Glass | `rgba(255,255,255,0.82)` | HUDs flotantes con blur |

### Tipografía (`app_text_styles.dart`):
| Fuente | Uso |
|--------|-----|
| **Space Grotesk** | Headlines, títulos, fases de partida |
| **Plus Jakarta Sans** | Body, microcopy, botones, anotaciones |
| **JetBrains Mono** | **Solo telemetría**: coordenadas, clocks, eval, depth, % |

### Componentes clave (`widgets/`):
| Widget | Descripción |
|--------|-------------|
| `EvaluationBar` | Horizontal/Vertical + badge JetBrains Mono |
| `ChessClock` | Pill clocks + pulse dot activo + low-time amber |
| `MoveHistory` | Chips horizontales con quality dots (brilliant/best/mistake/blunder) |
| `GlassCard` / `GlassHUD` | Glassmorphism con `BackdropFilter.blur(16)` |
| `TacticalCard` | Card blanca + slate border + título Space Grotesk |
| `TelemetryPill` | Pill slate con label + valor JetBrains Mono |

---

## 6. Pantallas — Detalle Lógico

### 1. LoginScreen (`login_screen.dart`)
- **AuthProvider** (via `AuthWrapper`) + loading skeleton
- **Form**: Email + Password + "Recordarme"
- **Toggle**: Login ↔ Register (misma pantalla, `_isLogin` boolean)
- **Validación**: Email regex, password ≥ 6 chars, confirmación en register
- **Error handling**: SnackBar/inline desde `auth.error`

### 2. ModeSelectionScreen (`mode_selection_screen.dart` — reemplazó a Onboarding/Diagnostic)
- "¿Qué quieres hacer ahora?" (diseño `03_seleccion_de_modo`)
- **Diagnóstico por rondas**: 3 partidas cortas seguidas contra Stockfish
  fijo (`_nivelDiagnostico = 10`) → promedia precisión para calcular el nivel
- **Test rápido**: 1 ronda, nivel bajo (`_nivelTestRapido = 2`)
- Navega a `/game` con `esDiagnostico`, `diagnosticoRonda`, `diagnosticoTotalRondas`
  y acumula `diagnosticoPrecisiones` entre rondas → al terminar, `/evaluation-result`

### 3. ConfigScreen (`config_screen.dart`)
- **Oponente**: Radio cards (Stockfish habilitado, Modelo IA disabled "Próximamente")
- **Nivel**: Slider 1-20 con labels (Principiante/Club/Experto/Maestro/GM)
- **Feedback toggle**: Switch (retroalimentación en vivo)
- **Botón**: "Comenzar Partida" → `context.go('/game', extra: {opponent, level, enableFeedback})`

### 4. GameScreen (`game_screen.dart`)
- **TopBar**: Oponente + nivel + menu (pausa, config, rendirse)
- **EvaluationBar** vertical (lado derecho) — `VerticalEvaluationBar`
- **ChessClock** dual (blancas/negras) con pulse dot turno activo
- **Tablero**: `AspectRatio 1:1` + `GridView 8x8` + coordenadas overlay
- **AnalysisPanel** (si enableFeedback): Evaluation + Best Move + Win%
- **MoveHistory** horizontal scroll (chips con quality dots)
- **Modo diagnóstico**: rondas encadenadas + ronda de evaluación (ver item 2)

### 5. HomeScreen (`home_screen.dart`)
- **TopBar**: Avatar + nombre + nivel + Streak pill (amber)
- **HeroBanner**: Gradient verde + CTA "Jugar" → `/config`
- **StatsRow**: 3 métricas (Partidas, Victorias, Precisión) con divider
- **SkillsProgressCard**: Radar chart (CustomPaint) + 6 skill bars animados
- **QuickActions**: 4 cards (Jugar, **Aprender → `/learning-path`**, Progreso, Config)
- **BottomNavBar**: 4 tabs (Home, Stats, Progress, Profile)

### 6. Victory/Defeat Screens
- **Ilustración custom** (CustomPaint: trofeo dorado / reyes caídos)
- **MetricsRow**: 3 columnas (Precisión, Movimientos, Evaluación final)
- **Chart evolución** (CustomPaint: área verde/roja + líneas)
- **AdviceBox** (derrota) / QuoteBadge (victoria)
- **Actions**: "Inicio" / "Otra partida" / "Reintentar"

### 7. LearningPathScreen + Lecciones (módulo Aprender)
- **LearningPathScreen** (`/learning-path`): compone los widgets del camino
  sobre el `LearningPathController` (detalle completo en la sección 8).
- **Lecciones** por capítulo (`/learning/board-basics`, `/learning/pieces`,
  `/learning/ranks-files`, `/learning/initial-position`): pantallas de lección
  reutilizan la base de UI de `learning_widgets.dart`.

---

## 7. Módulo de Aprendizaje ("Camino de Maestría")

Arquitectura en capas: la lógica de negocio vive en capas sin Flutter y la UI
solo compone widgets reutilizables y dinámicos.

```
models/learning/learning_models.dart        → Entidades pure Dart (sin Flutter)
services/learning/learning_service.dart     → Catálogo + reglas de derivación
services/learning/learning_path_controller.dart → Estado reactivo (ChangeNotifier)
widgets/learning/…                           → Widgets dinámicos y reutilizables
screens/learning/learning_path_screen.dart  → Composición (sin lógica)
```

### Entidades (`models/learning/learning_models.dart`)
| Entidad | Descripción |
|---------|-------------|
| `ChapterStatus` | `completed` / `inProgress` / `available` / `locked` |
| `PathAlignment` | `left` / `center` / `right` (péndulo S del camino) |
| `ChapterSymbol` | Símbolo del capítulo (board, queen, knight, capture, checkmate, strategy, trophy, start, pawn). Se guarda como **enum, no IconData**, para que los modelos sigan siendo pure Dart; `ChapterSymbolIcon` lo mapea a IconData/glifos |
| `LearningChapter` | id, title, subtitle, symbol, alignment, xp, stepsTotal, route (nullable), description, isBoss |
| `LearningUnit` | Unidad que agrupa capítulos (badge, título, descripción, symbol) |
| `LearningProgress` | Estado del jugador: `completedChapters`, `activeChapterIndex`, `activeChapterSteps`, `xp`, `streakDays`, `nivel`, `rankLabel`. `inicial()` = semilla demo del mockup (3 completados, cap. 4 activo 3/8 pasos, 350 XP, racha 3, nivel 4, rank "Aprendiz Táctico") → 38% completado, "5 lecciones pendientes" |
| `ResolvedChapter` | Capítulo + estado derivado + stepsDone (par de presentación) |

### LearningService (`services/learning/learning_service.dart`)
- **Catálogo**: `unidadInicial()` define 8 capítulos ("Fundamentos y Táctica
  Inicial"). Cap. 1-4 con `route` a lecciones existentes; cap. 5-8 sin ruta
  aún (bloqueados/por construir).
- **Regla de desbloqueo** (`resolver`): secuencial — capítulos antes de
  `completedChapters` → `completed`; índice activo → `inProgress`; el siguiente
  → `available`; el resto → `locked`. Corrige `activeChapterIndex <
  completedChapters` con clamp.
- Métricas: `fraccionCompletada()` (0..1), `leccionesPendientes()` (coincide
  con la métrica del mockup), `capituloActivo()`, `xpTotal()`.

### LearningPathController (`services/learning/learning_path_controller.dart`)
- `ChangeNotifier`; recibe `LearningService` y `LearningProgress` opcionales
  (inyectables para tests; a futuro la fuente puede ser la API sin tocar UI).
- Getters reactivos: `unidad`, `capitulos` (List<ResolvedChapter>),
  `capituloActivo`, `fraccionCompletada`, `leccionesPendientes`, `xp`, `racha`,
  `nivel`, `rankLabel`, `capitulosCompletados`, `totalCapitulos`, `xpTotal`.
- Acciones: `completarPaso()` (suma XP proporcional por paso; auto-completa el
  capítulo al llegar al último) y `marcarCapituloCompletado(chapterId, xpGanada)`.

### Widgets (`widgets/learning/`)
| Widget | Descripción |
|--------|-------------|
| `LearningPathHeader` + `StreakBadge` | Cabecera: volver, título "Camino de Maestría", label "APRENDER", racha 🔥 |
| `LearningPathProgressCard` | Nivel/rank, XP, barra de progreso, "N de 8 capítulos listos", lecciones pendientes |
| `LearningPathUnitBanner` | Banner de unidad en curso con badge "EN PROGRESO" |
| `LearningPath` | Orquestador: pendulo S de nodos + conectores + partículas decorativas (♟ ♝ ♜) |
| `ChapterNode` | Nodo circular dinámico según estado (completado, en curso, disponible, bloqueado, jefe final) + badges; para el capítulo activo embebe `ActiveChapterCard` con "Continuar Lección" |
| `ActiveChapterCard` | Card del capítulo en curso: badge de avance, título, descripción, botón continuar |
| `PathConnector` | Curvas entre nodos según par: `completed` (sólido), `activeLeap` (gradiente primary→teal), `upcoming` (dash), `locked` (dash claro). Comparte `pathSideOffset = 40` (const) |
| `ChapterSymbolIcon` | Mapea `ChapterSymbol` → IconData o glifo (♟♞♛♜♝ para piezas sin icono Material) |

Geometría del péndulo S: `PathAlignment` alterna los nodos entre centro, borde
izquierdo y borde derecho; los conectores dibujan curvas bezier entre los
anclajes usando las mismas fracciones de anclaje.

### Pantalla y feedback
- `LearningPathScreen` (`/learning-path`): `ChangeNotifierProvider` +
  `context.watch<LearningPathController>`; sin lógica de negocio propia.
- Nodos con `route` → `context.go(route)` (lecciones existentes).
- Nodos bloqueados o sin lección → `SnackBar` ("Completa el capítulo anterior…"
  / "Esta lección llega pronto."). Los nodos bloqueados son tappables por diseño.

### Tests
- `test/learning_path_test.dart`: unit tests de `LearningService` (8),
  `LearningPathController` (3, estado + XP + auto-completado) y widget tests de
  la pantalla (4) con stub de `GoRouter`.
- `test/learning_screens_test.dart`: render sin errores de las 4 lecciones en
  375×667 y 430×932.

---

## 8. Integración Backend (AuthApiService)

```dart
// lib/services/auth_api_service.dart
class AuthApiService {
  Dio _dio (baseUrl: 'http://10.0.2.2:8000')  // 10.0.2.2 = host desde Android emulator
  
  Interceptors:
    - Request: añade Authorization: Bearer <access_token>
    - Error 401: auto-refresh con /auth/refresh → retry request
  
  Métodos:
    - register(email, password, nombre) → AuthResponse
    - login(email, password) → AuthResponse + guarda tokens
    - logout() → limpia SecureStorage
    - hasValidToken() → bool
    - getCurrentUser() → GET /auth/me
}
```

### Endpoints usados:
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/registro` | Registro → `{usuario, tokens}` |
| POST | `/auth/login` | Login → `{usuario, tokens}` |
| POST | `/auth/refresh` | Refresh token → nuevo access_token |
| GET | `/auth/me` | Usuario actual (requiere Bearer) |

---

## 9. Dependencias Clave (`pubspec.yaml`)

```yaml
dependencies:
  flutter: sdk: flutter
  go_router: ^14.2.0          # Routing declarativo
  provider: ^6.1.2            # State management
  dio: ^5.5.0+1               # HTTP client
  flutter_secure_storage: ^9.0.0  # Tokens seguros
  google_fonts: ^6.2.1        # Fuentes (Space Grotesk, Plus Jakarta Sans, JetBrains Mono)
  fl_chart: ^0.68.0           # Gráficos (radar, líneas)
  shared_preferences: ^2.2.3  # Onboarding completado, preferencias
  crypto: ^3.0.3              # SHA-256 (auth local legacy)
```

---

## 10. Build & Run

### Android (Emulador):
```bash
# 1. Backend
cd /path/to/Ajedrez
PYTHONPATH=. DATABASE_URL=sqlite:///./test.db python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 2. Emulador
flutter emulators --launch Pixel_9a

# 3. App
cd app_movil && flutter run -d emulator-5554
```

### iOS (Device):
```bash
open ios/Runner.xcworkspace
# Seleccionar device "Iphone Luis Angel" → ▶️
```

### Build APK:
```bash
flutter build apk --debug
# Output: build/app/outputs/flutter-apk/app-debug.apk
```

---

## 11. Archivos Legacy (Auth Local — No Usar)

Estos archivos existen pero **no se usan** en el flujo actual (mantenidos por referencia):
- `lib/services/local_auth_service.dart`
- `lib/services/local_auth_provider.dart`
- `lib/services/local_auth_wrapper.dart`

El flujo actual usa `AuthProvider` + `AuthApiService` (backend real).

---

## 12. Pendientes / TODO

| Área | Tarea |
|------|-------|
| **Fuentes** | Descargar 12 `.ttf` a `assets/fonts/` (ver `assets/fonts/README.md`) |
| **Assets** | SVGs para piezas, trofeos, ilustraciones (ver `assets/images/README.md`) |
| **Tablero real** | Integrar `python-chess` vía FFI o mover validación a backend |
| **HU14** | Implementar `StatsTab` / `ProgressTab` / `ProfileTab` reales |
| **HU4** | Pipeline Colab reentrenamiento + evaluación modelo vs Stockfish |
| **HU6** | Conectar `GameScreen` con WebSocket/analysis en vivo |
| **Aprender** | Rutas de lección + contenido de capítulos 5-8 del camino (hoy muestran SnackBar) |
| **Aprender** | Persistir `LearningProgress` (hoy es memoria/semilla demo) |
| **Tests** | Widget tests de pantallas restantes (stats/progress/profile) + integration tests |

> ✅ HU12 (pantalla "Camino de Maestría" + lecciones) implementada y testeada:
> `test/learning_path_test.dart` + `test/learning_screens_test.dart`.

---

## 13. Referencias Rápidas

| Archivo | Ubicación |
|---------|-----------|
| Entry point | `lib/main.dart` |
| Tema completo | `lib/theme/app_theme.dart` |
| Colores | `lib/theme/app_colors.dart` |
| Tipografía | `lib/theme/app_text_styles.dart` |
| Auth provider | `lib/services/auth_provider.dart` |
| API client | `lib/services/auth_api_service.dart` |
| Router | `lib/main.dart` (función `crearRouter`) |
| Pantallas | `lib/screens/` |
| Widgets | `lib/widgets/` |
| Modelos Aprender | `lib/models/learning/learning_models.dart` |
| Servicio Aprender | `lib/services/learning/learning_service.dart` |
| Controller Aprender | `lib/services/learning/learning_path_controller.dart` |
| Widgets Aprender | `lib/widgets/learning/` |
| Pantalla camino | `lib/screens/learning/learning_path_screen.dart` |
| Lecciones | `lib/screens/learning/` |
| Tests Aprender | `test/learning_path_test.dart` |