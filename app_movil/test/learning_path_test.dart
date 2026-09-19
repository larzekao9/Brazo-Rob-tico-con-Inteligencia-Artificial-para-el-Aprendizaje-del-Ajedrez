import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:chessia_app/models/learning/learning_models.dart';
import 'package:chessia_app/services/learning/learning_path_controller.dart';
import 'package:chessia_app/services/learning/learning_service.dart';
import 'package:chessia_app/screens/learning/learning_path_screen.dart';
import 'package:chessia_app/theme/app_theme.dart';

void main() {
  group('LearningService', () {
    const service = LearningService();
    final unidad = service.unidadInicial();
    final progreso = LearningProgress.inicial();

    test('hay 8 capítulos en la unidad inicial', () {
      expect(unidad.chapters.length, 8);
    });

    test('resolver asigna estados secuenciales de desbloqueo', () {
      final r = service.resolver(unidad, progreso);
      expect(r[0].status, ChapterStatus.completed);
      expect(r[1].status, ChapterStatus.completed);
      expect(r[2].status, ChapterStatus.completed);
      expect(r[3].status, ChapterStatus.inProgress);
      expect(r[4].status, ChapterStatus.available);
      expect(r[5].status, ChapterStatus.locked);
      expect(r[8 - 1].status, ChapterStatus.locked);
    });

    test('los pasos resueltos son totales/parciales según el estado', () {
      final r = service.resolver(unidad, progreso);
      expect(r[0].stepsDone, unidad.chapters[0].stepsTotal);
      expect(r[3].stepsDone, progreso.activeChapterSteps);
      expect(r[4].stepsDone, 0);
    });

    test('fraccionCompletada = completados / total', () {
      expect(service.fraccionCompletada(unidad, progreso), closeTo(3 / 8, 1e-9));
    });

    test('leccionesPendientes = pasos faltantes del capítulo en curso', () {
      // 8 pasos totales, 3 hechos → 5 pendientes (coincide con el mockup).
      expect(service.leccionesPendientes(unidad, progreso), 5);
    });

    test('capituloActivo devuelve el capítulo en progreso', () {
      final activo = service.capituloActivo(unidad, progreso);
      expect(activo?.chapter.id, 'cap-4-movimiento');
    });

    test('resolver corrige un activeChapterIndex menor al de completados', () {
      const invalido = LearningProgress(
        completedChapters: 1,
        activeChapterIndex: 0,
        activeChapterSteps: 2,
        xp: 0,
        streakDays: 0,
        nivel: 1,
        rankLabel: 'X',
      );
      final r = service.resolver(unidad, invalido);
      expect(r[0].status, ChapterStatus.completed);
      expect(r[1].status, ChapterStatus.inProgress);
      expect(r[2].status, ChapterStatus.available);
    });
  });

  group('LearningPathController', () {
    test('completarPaso acumula XP y pasos del capítulo activo', () {
      final c = LearningPathController();
      final xp0 = c.xp;
      c.completarPaso();
      expect(c.capituloActivo?.stepsDone, 4);
      expect(c.xp, greaterThan(xp0));
    });

    test('completarPaso auto-completa el capítulo al llegar al final', () {
      final c = LearningPathController(
        progress: const LearningProgress(
          completedChapters: 0,
          activeChapterIndex: 0,
          activeChapterSteps: 3, // cap-1 tiene 4 pasos
          xp: 0,
          streakDays: 0,
          nivel: 1,
          rankLabel: 'X',
        ),
      );
      c.completarPaso(); // 4to paso → completa cap-1
      expect(c.capitulosCompletados, 1);
      expect(c.capituloActivo?.chapter.id, 'cap-2-piezas');
    });

    test('marcarCapituloCompletado avanza el índice activo', () {
      final c = LearningPathController();
      c.marcarCapituloCompletado('cap-4-movimiento');
      expect(c.capitulosCompletados, 4);
      expect(c.capituloActivo?.chapter.id, 'cap-5-captura');
    });
  });

  group('LearningPathScreen', () {
    GoRouter buildRouter() => GoRouter(
          initialLocation: LearningPathScreen.routeName,
          routes: [
            GoRoute(path: '/home', builder: (_, __) => const _Stub(label: 'home')),
            GoRoute(
              path: LearningPathScreen.routeName,
              builder: (_, __) => const LearningPathScreen(),
            ),
            GoRoute(
              path: '/learning/board-basics',
              builder: (_, __) => const _Stub(label: 'board-basics'),
            ),
          ],
        );

    Future<void> pumpPath(WidgetTester tester, Size size) async {
      tester.view.physicalSize = size * 3;
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(
        MaterialApp.router(routerConfig: buildRouter(), theme: AppTheme.lightTheme),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('renderiza el camino sin errores (430x932)', (tester) async {
      await pumpPath(tester, const Size(430, 932));
      expect(find.text('APRENDER'), findsOneWidget);
      expect(find.text('Camino de Maestría'), findsOneWidget);
      expect(find.text('Unidad 1: Fundamentos y Táctica Inicial'), findsOneWidget);
      expect(find.textContaining('% completado'), findsOneWidget);

      final scroll = find.byType(Scrollable).first;
      for (var i = 0; i < 40; i++) {
        await tester.drag(scroll, const Offset(0, -600));
        await tester.pump();
        final ex = tester.takeException();
        expect(ex, isNull, reason: 'error durante scroll $i: $ex');
      }
    });

    testWidgets('renderiza el camino en pantalla chica sin overflow', (tester) async {
      await pumpPath(tester, const Size(375, 667));
      final scroll = find.byType(Scrollable).first;
      for (var i = 0; i < 40; i++) {
        await tester.drag(scroll, const Offset(0, -600));
        await tester.pump();
        final ex = tester.takeException();
        expect(ex, isNull, reason: 'error durante scroll $i: $ex');
      }
    });

    testWidgets('tocar un capítulo bloqueado muestra aviso', (tester) async {
      await pumpPath(tester, const Size(430, 932));
      final scroll = find.byType(Scrollable).first;
      await tester.scrollUntilVisible(
        find.text('Jaque y jaque mate'),
        300,
        scrollable: scroll,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Jaque y jaque mate'));
      await tester.pump();
      expect(
        find.text('Completa el capítulo anterior para desbloquear este.'),
        findsOneWidget,
      );
    });

    testWidgets('tocar un capítulo completado abre su lección', (tester) async {
      await pumpPath(tester, const Size(430, 932));
      await tester.tap(find.text('El tablero'));
      await tester.pumpAndSettle();
      expect(find.text('board-basics'), findsOneWidget);
    });
  });
}

class _Stub extends StatelessWidget {
  final String label;
  const _Stub({required this.label});

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: Center(child: Text(label)));
  }
}