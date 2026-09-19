import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:chessia_app/screens/home_screen.dart';
import 'package:chessia_app/services/auth_api_service.dart';
import 'package:chessia_app/services/auth_provider.dart';
import 'package:chessia_app/services/partida.dart';
import 'package:chessia_app/theme/app_theme.dart';

/// Backend falso: hay estadísticas reales del jugador (GET /usuario/estadisticas).
class _ApiConEstadisticas extends AuthApiService {
  @override
  Future<bool> hasStoredToken() async => false;

  @override
  Future<EstadisticasUsuario> estadisticasUsuario() async => const EstadisticasUsuario(
        totalPartidas: 5,
        partidasGanadas: 3,
        partidasPerdidas: 1,
        partidasTablas: 1,
        winPercentPromedio: 60,
        rachaVictoriaActual: 2,
        precisionPromedio: 69.0,
        topErrores: [],
      );
}

Future<void> _montar(WidgetTester tester) async {
  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.lightTheme,
    home: ChangeNotifierProvider.value(
      value: AuthProvider(api: _ApiConEstadisticas()),
      child: const HomeScreen(),
    ),
  ));
  await tester.pump(); // initState + postFrame
  await tester.pump(); // resuelve cargarEstadisticas
}

void main() {
  testWidgets('La fila de métricas muestra las estadísticas reales del jugador',
      (WidgetTester tester) async {
    await _montar(tester);

    expect(find.text('5'), findsOneWidget);
    expect(find.text('3'), findsOneWidget);
    expect(find.text('69%'), findsOneWidget);
    // Ya no están los valores de ejemplo de la fila de métricas.
    expect(find.text('12'), findsNothing);
    expect(find.text('4'), findsNothing);
  });
}