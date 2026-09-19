import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:chessia_app/screens/learning/board_basics_screen.dart';
import 'package:chessia_app/screens/learning/pieces_screen.dart';
import 'package:chessia_app/screens/learning/ranks_files_screen.dart';
import 'package:chessia_app/screens/learning/initial_position_screen.dart';
import 'package:chessia_app/theme/app_theme.dart';

/// Recorre de punta a punta una pantalla de aprendizaje (con scroll hasta el
/// final) a un tamaño dado y falla si aparece cualquier error de layout o si
/// queda HTML crudo (`<strong>`) visible en pantalla.
Future<void> _verificarPantalla(
  WidgetTester tester,
  Widget pantalla, {
  required Size size,
  double dpr = 3.0,
  double topInset = 59,
}) async {
  tester.view.physicalSize = size * dpr;
  tester.view.devicePixelRatio = dpr;
  tester.view.padding = FakeViewPadding(top: topInset * dpr, bottom: 34 * dpr);
  tester.view.viewPadding = FakeViewPadding(top: topInset * dpr, bottom: 34 * dpr);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(MaterialApp(theme: AppTheme.lightTheme, home: pantalla));
  await tester.pump();

  // Scroll completo hasta tocar fondo para forzar el layout de todo.
  final scroll = find.byType(Scrollable).first;
  for (var i = 0; i < 30; i++) {
    await tester.drag(scroll, const Offset(0, -600));
    await tester.pump();
    final ex = tester.takeException();
    expect(ex, isNull, reason: 'error durante scroll $i: $ex');
  }

  // Ningún texto debe mostrar etiquetas HTML crudas.
  expect(find.textContaining('<strong'), findsNothing);
  expect(find.textContaining('</strong>'), findsNothing);
  expect(find.textContaining('class='), findsNothing);
}

void main() {
  const pantallas = <String, Widget>{
    'board-basics': BoardBasicsScreen(),
    'pieces': PiecesScreen(),
    'ranks-files': RanksFilesScreen(),
    'initial-position': InitialPositionScreen(),
  };

  // iPhone 14/15 Pro Max
  for (final entry in pantallas.entries) {
    testWidgets('${entry.key} se renderiza sin errores (430x932)', (tester) async {
      await _verificarPantalla(tester, entry.value, size: const Size(430, 932));
    });
  }

  // iPhone SE (pantalla chica: donde aparecen los overflows)
  for (final entry in pantallas.entries) {
    testWidgets('${entry.key} se renderiza sin errores (375x667)', (tester) async {
      await _verificarPantalla(tester, entry.value, size: const Size(375, 667), topInset: 20);
    });
  }
}
