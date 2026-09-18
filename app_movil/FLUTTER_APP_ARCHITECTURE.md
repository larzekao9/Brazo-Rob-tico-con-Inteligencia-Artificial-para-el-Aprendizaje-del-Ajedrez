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
│   ├── theme.dart               # Barrel export del Design System
│   ├── theme/
│   │   ├── app_colors.dart      # Paleta completa (semántica, no solo valores)
│   │   ├── app_text_styles.dart # 13 estilos tipográficos (3 fuentes)
│   │   ├── app_spacing.dart     # Espaciado 4px/8px, radius, gutters
│   │   ├── app_shadows.dart     # 4 niveles elevation + neural glows + glass
│   │   └── app_theme.dart       # ThemeData M3 + extensiones Chess/Glass
│   ├── services/
│   │   ├── services.dart        # Barrel export
│   │   ├── local_auth_service.dart    # Auth local (SharedPreferences + SHA-256) — LEGACY
│   │   ├── local_auth_provider.dart   # Provider auth local — LEGACY
│   │   ├── local_auth_wrapper.dart    # Wrapper provider local — LEGACY
│   │   ├── auth_api_service.dart      # Cliente HTTP (Dio) + FlutterSecureStorage + Interceptors
│   │   ├── auth_provider.dart         # Provider principal (AuthProvider) — BACKEND REAL
│   │   ├── chess_api.dart             # API partidas, análisis, motor
│   │   └── partida.dart               # Modelos Partida, Analisis, etc.
│   ├── widgets/
│   │   ├── widgets.dart         # Barrel export
│   │   ├── evaluation_bar.dart  # Barra eval horizontal/vertical (JetBrains Mono badge)
│   │   ├── chess_clock.dart     # Relojes pill + pulse dot + low-time amber
│   │   ├── move_history.dart    # Chips horizontales con quality dots
│   │   └── glass_card.dart      # GlassCard, GlassHUD, TacticalCard, TelemetryPill
│   └── screens/
│       ├── screens.dart         # Barrel export
│       ├── login_screen.dart    # Login/Register email+password (AuthWrapper)
│       ├── onboarding_screen.dart  # 9 tarjetas interactivas (PageView)
│       ├── diagnostic_screen.dart  # 8 preguntas, calcula nivel 1-20
│       ├── config_screen.dart   # Selector oponente + slider nivel 1-20
│       ├── game_screen.dart     # Tablero + clocks + eval bar + análisis panel
│       ├── evaluation_result_screen.dart # Trofeo animado + rank + métricas
│       ├── home_screen.dart     # Dashboard (stats, radar chart, skills, actions)
│       ├── victory_screen.dart  # Trofeo dorado + chart evolución + confeti
│       └── defeat_screen.dart   # Reyes ilustración + chart caída + advice
```

---

## 3. Flujo de Navegación (GoRouter)

```
Rutas públicas:
  /login          → LoginScreen (AuthWrapper)
  /onboarding     → OnboardingScreen
  /diagnostic     → DiagnosticScreen
  /config         → ConfigScreen (recibe diagnosticLevel)

Rutas autenticadas (redirect en GoRouter):
  /home           → HomeScreen (BottomNav: Home, Stats, Progress, Profile)
  /game           → GameScreen (partidaId, opponent, level, enableFeedback)
  /victory        → VictoryScreen (playerName, accuracy, moves, finalEval, opponent)
  /defeat         → DefeatScreen (playerName, accuracy, moves, finalEval, opponent)
  /evaluation-result → EvaluationResultScreen (level, rank, accuracy, gamesPlayed)

Redirect logic:
  - Si !loggedIn && ruta != /login → /login
  - Si loggedIn && ruta == /login → /onboarding (o /home si ya completó onboarding)
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
- **AuthWrapper** → `AuthProvider` + loading skeleton
- **Form**: Email + Password + "Recordarme"
- **Toggle**: Login ↔ Register (misma pantalla, `_isLogin` boolean)
- **Validación**: Email regex, password ≥ 6 chars, confirmación en register
- **Error handling**: SnackBar/inline desde `auth.error`

### 2. OnboardingScreen (`onboarding_screen.dart`)
- **PageView** 9 tarjetas (`OnboardingCard` data class)
- Cada tarjeta: pieza (emoji), nombre, descripción, movimiento, ejemplo interactivo (placeholder)
- **Indicador**: Dots animados abajo
- **Completado**: `context.go('/diagnostic')` (persistir en backend/local después)

### 3. DiagnosticScreen (`diagnostic_screen.dart`)
- **8 preguntas** (experiencia, aperturas, tácticas, finales, rating, estudio, objetivos, estilo)
- **Progress bar** lineal arriba
- **Opciones**: Radio buttons estilo cards (selección visual)
- **Navegación**: Prev/Next + "Saltar" solo en primera
- **Cálculo nivel**: Score 0-12 → Principiante (5), Intermedio (12), Avanzado (18)
- **Navega**: `context.go('/config', extra: level)`

### 4. ConfigScreen (`config_screen.dart`)
- **Oponente**: Radio cards (Stockfish habilitado, Modelo IA disabled "Próximamente")
- **Nivel**: Slider 1-20 con labels (Principiante/Club/Experto/Maestro/GM)
- **Feedback toggle**: Switch (retroalimentación en vivo)
- **Botón**: "Comenzar Partida" → `context.go('/game', extra: {opponent, level, enableFeedback})`

### 5. GameScreen (`game_screen.dart`)
- **TopBar**: Oponente + nivel + menu (pausa, config, rendirse)
- **EvaluationBar** vertical (lado derecho) — `VerticalEvaluationBar`
- **ChessClock** dual (blancas/negras) con pulse dot turno activo
- **Tablero**: `AspectRatio 1:1` + `GridView 8x8` + coordenadas overlay
- **AnalysisPanel** (si enableFeedback): Evaluation + Best Move + Win%
- **MoveHistory** horizontal scroll (chips con quality dots)

### 6. HomeScreen (`home_screen.dart`)
- **TopBar**: Avatar + nombre + nivel + Streak pill (amber)
- **HeroBanner**: Gradient verde + CTA "Jugar" → `/config`
- **StatsRow**: 3 métricas (Partidas, Victorias, Precisión) con divider
- **SkillsProgressCard**: Radar chart (CustomPaint) + 6 skill bars animados
- **QuickActions**: 4 cards (Jugar, Aprender, Progreso, Config)
- **BottomNavBar**: 4 tabs (Home, Stats, Progress, Profile)

### 7. Victory/Defeat Screens
- **Ilustración custom** (CustomPaint: trofeo dorado / reyes caídos)
- **MetricsRow**: 3 columnas (Precisión, Movimientos, Evaluación final)
- **Chart evolución** (CustomPaint: área verde/roja + líneas)
- **AdviceBox** (derrota) / QuoteBadge (victoria)
- **Actions**: "Inicio" / "Otra partida" / "Reintentar"

---

## 7. Integración Backend (AuthApiService)

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

## 8. Dependencias Clave (`pubspec.yaml`)

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

## 9. Build & Run

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

## 10. Archivos Legacy (Auth Local — No Usar)

Estos archivos existen pero **no se usan** en el flujo actual (mantenidos por referencia):
- `lib/services/local_auth_service.dart`
- `lib/services/local_auth_provider.dart`
- `lib/services/local_auth_wrapper.dart`

El flujo actual usa `AuthProvider` + `AuthApiService` (backend real).

---

## 11. Pendientes / TODO

| Área | Tarea |
|------|-------|
| **Fuentes** | Descargar 12 `.ttf` a `assets/fonts/` (ver `assets/fonts/README.md`) |
| **Assets** | SVGs para piezas, trofeos, ilustraciones (ver `assets/images/README.md`) |
| **Tablero real** | Integrar `python-chess` vía FFI o mover validación a backend |
| **HU14** | Implementar `StatsTab` / `ProgressTab` / `ProfileTab` reales |
| **HU4** | Pipeline Colab reentrenamiento + evaluación modelo vs Stockfish |
| **HU6** | Conectar `GameScreen` con WebSocket/analysis en vivo |
| **Tests** | Unit tests providers, widget tests screens, integration tests |

---

## 12. Referencias Rápidas

| Archivo | Ubicación |
|---------|-----------|
| Entry point | `lib/main.dart` |
| Tema completo | `lib/theme/app_theme.dart` |
| Colores | `lib/theme/app_colors.dart` |
| Tipografía | `lib/theme/app_text_styles.dart` |
| Auth provider | `lib/services/auth_provider.dart` |
| API client | `lib/services/auth_api_service.dart` |
| Router | `lib/main.dart` (variable `_router`) |
| Pantallas | `lib/screens/` |
| Widgets | `lib/widgets/` |