# Arquitectura Flutter — ChessIA App Móvil

## Visión General
**Clean Architecture simplificada + MVVM con Provider** — Capas separadas, estado global con `ChangeNotifier`, navegación declarativa con `go_router`.

---

## Estructura de Carpetas

```
app_movil/lib/
├── main.dart                 # Entry point, router, providers globales
├── models.dart               # Entidades de dominio (AppUser, OpponentType, MoveEntry)
├── theme/                    # Design System centralizado
│   ├── app_colors.dart       # Paleta (primary, secondary, surface, etc.)
│   ├── app_text_styles.dart  # Tipografías (display, headline, body, label)
│   ├── app_spacing.dart      # Espaciado consistente (spaceXs..spaceXxl, margin)
│   ├── app_shadows.dart      # Sombras (card, elevated, glow)
│   ├── app_radius.dart       # Border radius (sm, md, lg, xl, full)
│   ├── app_theme.dart        # ThemeData + ThemeExtensions (ChessTheme, GlassMorphism)
│   └── theme.dart            # Barrel export
├── services/                 # Capa de datos / lógica de negocio
│   ├── api_config.dart       # URL base dinámica (--dart-define, IP local, emulador)
│   ├── auth_api_service.dart # HTTP Auth (Dio + JWT + refresh automático + secure storage)
│   ├── auth_provider.dart    # ChangeNotifier: sesión, user, login, logout, guardarNivelEstimado
│   ├── chess_api.dart        # HTTP Partidas: crear, mover, analizar, historial
│   ├── local_auth_service.dart      # Biometría / PIN (opcional)
│   ├── local_auth_provider.dart     # Provider biometría
│   ├── local_auth_wrapper.dart      # Wrapper autenticación local
│   ├── auth_service.dart       # Helper tokens
│   ├── auth_wrapper.dart       # Wrapper auth global
│   └── partida.dart            # Modelo Partida + MoveEntry
├── widgets/                  # UI Kit reutilizable (StatelessWidget)
│   ├── learning_widgets.dart # LearningCard, InfoCallout, QuickCheck, LearningProgressHeader,
│   │                         # LearningBottomNav, InteractiveChessBoard, PieceRow,
│   │                         # ChessPieceSvg, PieceCountSummary, GoldenRuleCallout,
│   │                         # MoveVsCaptureSection, FinalAdviceCallout
│   ├── chess_board.dart      # Tablero interactivo (reutilizable)
│   ├── evaluation_bar.dart   # Barra de evaluación Stockfish
│   ├── move_history.dart     # Historial de movimientos
│   ├── app_bar_custom.dart   # AppBar personalizada
│   ├── buttons.dart          # Botones reutilizables
│   ├── cards.dart            # GlassCard, InfoCard, etc.
│   ├── dialogs.dart          # Diálogos comunes
│   ├── layout.dart           # Layouts base (SafeArea, Padding, etc.)
│   └── widgets.dart          # Barrel export
├── screens/                  # Pantallas (Vistas)
│   ├── learning/             # HU12 - Aprendizaje (4 pantallas)
│   │   ├── board_basics_screen.dart      # Tablero: filas, columnas, casillas
│   │   ├── pieces_screen.dart            # Piezas: movimiento, valor, captura
│   │   ├── ranks_files_screen.dart       # Filas/Columnas: coordenadas algebraicas
│   │   └── initial_position_screen.dart  # Posición inicial completa
│   ├── login_screen.dart              # Login / Registro
│   ├── mode_selection_screen.dart     # Test rápido (1 partida) / Mide tu nivel (3 partidas)
│   ├── config_screen.dart             # Configuración: nivel, sonido, biometría
│   ├── game_screen.dart               # Partida: tablero, reloj, análisis, diagnóstico
│   ├── evaluation_result_screen.dart  # Resultado diagnóstico: nivel, rango, precisión, botón "Ir al inicio"
│   ├── home_screen.dart               # Dashboard: stats, progreso, perfil, nivel/rango visible
│   ├── victory_screen.dart            # Victoria
│   ├── defeat_screen.dart             # Derrota
│   └── screens.dart                   # Barrel export
├── screens.dart              # Barrel export screens/
├── widgets.dart              # Barrel export widgets/
├── services.dart             # Barrel export services/
└── theme.dart                # Barrel export theme/
```

---

## Flujo de Datos Principal

```
┌─────────────────────┐
│   Usuario abre app  │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  AuthWrapper        │──► ¿Token válido?
│  (main.dart)        │
└─────────┬───────────┘
          ▼
   ┌──────┴──────┐
   ▼             ▼
 Login        HomeScreen
   │             │
   ▼             ▼
AuthProvider  AuthProvider.watch(user)
  .login()        │
   │              ▼
   ▼       ┌───────────────┐
HomeScreen│  _TopBar muestra  │
          │  "Rango • Nivel X"│
          └───────────────┘
```

### Flujo "Mide tu nivel" (Diagnóstico)

```
ModeSelectionScreen
      │
      ▼ (Test rápido: 1 partida nivel 2 / Mide tu nivel: 3 partidas nivel 10)
GameScreen (StatefulWidget)
      │
      ├── ChessApi.crearPartida(nivel)
      ├── ChessApi.mover(jugada) ───► Backend
      ├── ChessApi.analisisCompleto() ───► Precisión por jugada
      │
      ▼ (al terminar partidas)
_irAResultadoDiagnostico(promedioPrecisión)
      │
      ├── Calcula rango:
      │     ≥80% → Avanzado (nivel 18)
      │     ≥55% → Intermedio (nivel 11)
      │     <55% → Principiante (nivel 5)
      │
      ├── AuthProvider.guardarNivelEstimado(nivel, rango)
      │       └──► PATCH /auth/nivel-estimado (backend)
      │
      ▼
EvaluationResultScreen (recibe level, rank, accuracy, gamesPlayed)
      │
      ├── Muestra: "Nivel X • Rango" en badge del trofeo
      ├── Métricas: Nivel asignado, Precisión %, Partidas test
      │
      ▼ (botón)
"Ir al inicio" ──► context.go('/home')
      │
      ▼
HomeScreen (AuthProvider.watch → user.nivelEstimado/rangoEstimado)
```

---

## Patrones por Capa

| Capa | Patrón | Archivo Clave |
|------|--------|---------------|
| **Estado Global** | `ChangeNotifier` + `Provider` | `AuthProvider` |
| **Navegación** | `go_router` (declarativo, typed) | `main.dart` → `crearRouter(auth)` |
| **HTTP** | `Dio` + Interceptors | `AuthApiService`, `ChessApi` |
| **Tema** | `ThemeData` + `ThemeExtension` | `AppTheme.lightTheme`, `ChessThemeExtension` |
| **Componentes UI** | `StatelessWidget` compuestos | `LearningCard`, `InteractiveChessBoard` |
| **Pantallas** | `StatefulWidget` + `setState` | `GameScreen`, `ConfigScreen` |
| **Modelos** | Clases Dart puras + `fromJson`/`toJson` | `models.dart`, `partida.dart` |

---

## Dependencias Principales (pubspec.yaml)

```yaml
dependencies:
  flutter:
    sdk: flutter
  go_router: ^14.0+          # Navegación
  provider: ^6.1+            # Estado global
  dio: ^5.4+                 # HTTP client
  flutter_secure_storage: ^9.0+  # Tokens seguros
  local_auth: ^2.2+          # Biometría
  chess_vectors_icons: ^1.0+ # Iconos piezas (SVG)
  intl: ^0.19+               # Formato fechas
```

---

## Convenciones de Código

1. **Naming**: `snake_case` archivos, `PascalCase` clases, `camelCase` variables/métodos
2. **Barrels**: Cada carpeta tiene `archivo.dart` que re-exporta (`widgets.dart`, `screens.dart`, etc.)
3. **Tema**: Siempre usar `AppColors`, `AppTextStyles`, `AppSpacing` — nada hardcodeado
4. **Async**: `Future` + `async/await`, manejo de errores con `try/catch` + `ScaffoldMessenger`
5. **Navegación**: `context.go('/ruta')` o `context.push('/ruta')` — evitar `Navigator.push`
6. **Providers**: `context.watch<T>()` para rebuild, `context.read<T>()` para acciones puntuales

---

## Puntos de Extensión Futura

| Área | Archivo a tocar |
|------|-----------------|
| Nueva pantalla aprendizaje | `screens/learning/nueva_screen.dart` + ruta en `main.dart` |
| Nuevo endpoint API | `services/chess_api.dart` + modelo en `models.dart` |
| Cambio tema global | `theme/app_theme.dart` + `theme/app_colors.dart` |
| Nuevo estado global | Nuevo `ChangeNotifier` en `services/` + registrar en `main.dart` |
| Nueva métrica diagnóstico | `game_screen.dart` → `_irAResultadoDiagnostico` + `EvaluationResultScreen` |

---

## Comandos Útiles

```bash
# Desarrollo (iPhone real)
flutter run -d "00008150-000454663C20401C" --dart-define=API_BASE_URL=http://192.168.101.10:8000

# Desarrollo (emulador Android)
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

# Analizar código
flutter analyze

# Tests
flutter test

# Build release iOS
flutter build ios --release

# Limpiar
flutter clean && flutter pub get
```

---

## Backend Requerido (FastAPI)

- **Base URL**: `http://192.168.101.10:8000` (iPhone en red local)
- **Endpoints usados**:
  - `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`
  - `PATCH /auth/nivel-estimado` (guarda nivel/rango diagnóstico)
  - `GET /auth/me` (perfil usuario)
  - `POST /partida` (crear), `POST /partida/{id}/mover`, `GET /partida/{id}/analisis`
  - `GET /usuario/estadisticas`, `GET /usuario/historial-partidas`

---

## Notas de Implementación Actual

- ✅ **HU12 Aprendizaje**: 4 pantallas + widgets reutilizables (`learning_widgets.dart`)
- ✅ **Diagnóstico**: Test rápido (1 partida) + Mide tu nivel (3 partidas)
- ✅ **Persistencia nivel**: Backend + `AuthProvider` + `HomeScreen` muestra chip real
- ✅ **EvaluationResultScreen**: Badge "Nivel X • Rango" + botón "Ir al inicio"
- ⚠️ **Pendiente**: Permiso iOS "Red local" para conectar a backend en iPhone real