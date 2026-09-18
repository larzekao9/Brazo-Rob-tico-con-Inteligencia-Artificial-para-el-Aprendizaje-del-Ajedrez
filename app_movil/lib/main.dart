import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'theme/app_theme.dart';
import 'theme/app_colors.dart';
import 'models.dart';
import 'screens/login_screen.dart';
import 'screens/onboarding_screen.dart';
import 'screens/mode_selection_screen.dart';
import 'screens/config_screen.dart';
import 'screens/game_screen.dart';
import 'screens/evaluation_result_screen.dart';
import 'screens/home_screen.dart';
import 'screens/victory_screen.dart';
import 'screens/defeat_screen.dart';
import 'services/api_config.dart';
import 'services/auth_provider.dart';

/// Rutas visibles sin sesión. Todo lo demás exige un jugador logueado.
const _rutasPublicas = {'/splash', '/login'};

GoRouter crearRouter(AuthProvider auth) {
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: auth,
    redirect: (context, state) {
      final destino = state.matchedLocation;
      if (auth.isInitializing) {
        return destino == '/splash' ? null : '/splash';
      }
      if (!auth.isLoggedIn) {
        return destino == '/login' ? null : '/login';
      }
      if (_rutasPublicas.contains(destino)) {
        return '/onboarding';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const _SplashScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/mode-selection',
        builder: (context, state) => const ModeSelectionScreen(),
      ),
      GoRoute(
        path: '/config',
        builder: (context, state) {
          final level = state.extra as int? ?? 5;
          return ConfigScreen(diagnosticLevel: level);
        },
      ),
      GoRoute(
        path: '/game',
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>? ?? {};
          return GameScreen(
            partidaId: extra['partidaId'] as String,
            opponent: extra['opponent'] as OpponentType? ?? OpponentType.stockfish,
            level: extra['level'] as int? ?? 5,
            enableFeedback: extra['enableFeedback'] as bool? ?? true,
            esDiagnostico: extra['esDiagnostico'] as bool? ?? false,
            diagnosticoRonda: extra['diagnosticoRonda'] as int? ?? 1,
            diagnosticoTotalRondas: extra['diagnosticoTotalRondas'] as int? ?? 1,
            diagnosticoPrecisiones:
                (extra['diagnosticoPrecisiones'] as List?)?.cast<double>() ?? const [],
          );
        },
      ),
      GoRoute(
        path: '/evaluation-result',
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>? ?? {};
          return EvaluationResultScreen(
            level: extra['level'] as int? ?? 5,
            rank: extra['rank'] as String? ?? 'Principiante',
            accuracy: extra['accuracy'] as double? ?? 68.0,
            gamesPlayed: extra['gamesPlayed'] as int? ?? 10,
          );
        },
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/victory',
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>? ?? {};
          return VictoryScreen(
            playerName: extra['playerName'] as String? ?? 'Jugador',
            accuracy: extra['accuracy'] as int? ?? 88,
            moves: extra['moves'] as int? ?? 28,
            finalEval: extra['finalEval'] as double? ?? 2.3,
            opponent: extra['opponent'] as String? ?? 'Stockfish',
          );
        },
      ),
      GoRoute(
        path: '/defeat',
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>? ?? {};
          return DefeatScreen(
            playerName: extra['playerName'] as String? ?? 'Jugador',
            accuracy: extra['accuracy'] as int? ?? 62,
            moves: extra['moves'] as int? ?? 36,
            finalEval: extra['finalEval'] as double? ?? -2.1,
            opponent: extra['opponent'] as String? ?? 'Stockfish',
          );
        },
      ),
    ],
  );
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiConfig.cargar();
  runApp(const ChessIAApp());
}

class ChessIAApp extends StatefulWidget {
  /// `auth` se inyecta solo en tests (para no depender del almacenamiento
  /// seguro nativo); en la app real se crea acá.
  const ChessIAApp({super.key, this.auth});

  final AuthProvider? auth;

  @override
  State<ChessIAApp> createState() => _ChessIAAppState();
}

class _ChessIAAppState extends State<ChessIAApp> {
  late final AuthProvider _auth = widget.auth ?? AuthProvider();
  late final GoRouter _router = crearRouter(_auth);

  @override
  void dispose() {
    _router.dispose();
    _auth.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider<AuthProvider>.value(
      value: _auth,
      child: MaterialApp.router(
        title: 'ChessIA - Neural Grandmaster',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        routerConfig: _router,
      ),
    );
  }
}

/// Pantalla mínima mientras se comprueba si había una sesión guardada.
class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image(
              image: AssetImage('assets/images/logo.png'),
              width: 160,
              height: 160,
              fit: BoxFit.contain,
            ),
            SizedBox(height: 24),
            CircularProgressIndicator(color: AppColors.primary),
          ],
        ),
      ),
    );
  }
}
