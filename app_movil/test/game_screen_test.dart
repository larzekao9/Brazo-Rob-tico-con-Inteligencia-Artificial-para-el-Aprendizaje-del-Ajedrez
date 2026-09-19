import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:chessia_app/models.dart';
import 'package:chessia_app/screens/game_screen.dart';
import 'package:chessia_app/services/chess_api.dart';
import 'package:chessia_app/services/partida.dart';
import 'package:chessia_app/theme/app_theme.dart';

const _fenTras1d4c6 = 'rnbqkbnr/pp1ppppp/2p5/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2';

/// Backend falso: la partida ya tiene 1. d4 c6 (el estado que dejaba el
/// tablero en blanco en el iPhone) y Stockfish "responde" una evaluación.
class _ApiFalsa extends ChessApi {
  _ApiFalsa() : super.paraTests();

  @override
  Future<Partida> obtenerPartida(String partidaId) async => Partida(
        id: partidaId,
        tipoOponente: 'motor',
        nivel: 5,
        fen: _fenTras1d4c6,
        fenInicial: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        terminada: false,
        resultado: null,
        jugadas: const ['d4', 'c6'],
      );

  @override
  Future<AnalisisPosicion> analizarPosicion(String fen, int nivel) async =>
      AnalisisPosicion(jugada: 'e2e4', evaluacionCp: 40, mateEn: null);

  @override
  Future<List<String>> jugadasLegalesDesde(String partidaId, String casilla) async => const ['e3', 'e4'];
}

/// Backend que falla (sin red): la pantalla igual tiene que dibujar el
/// tablero con la posición inicial.
class _ApiCaida extends ChessApi {
  _ApiCaida() : super.paraTests();

  @override
  Future<Partida> obtenerPartida(String partidaId) async => throw Exception('sin backend');
}

Future<void> _montar(WidgetTester tester, {required Size fisico, required double dpr}) async {
  tester.view.physicalSize = fisico;
  tester.view.devicePixelRatio = dpr;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.lightTheme,
    home: const GameScreen(partidaId: 'p1', opponent: OpponentType.stockfish, level: 5, enableFeedback: true),
  ));
  await tester.pump();
  await tester.pump(const Duration(seconds: 1));
}

void main() {
  tearDown(() => ChessApi.instancia = _ApiCaida());

  testWidgets('Con jugadas hechas, el tablero y el historial se dibujan en un iPhone', (tester) async {
    ChessApi.instancia = _ApiFalsa();
    await _montar(tester, fisico: const Size(1206, 2622), dpr: 3.0);

    expect(tester.takeException(), isNull);
    expect(find.text('♔'), findsOneWidget);
    expect(find.text('♚'), findsOneWidget);
    expect(find.text('d4'), findsOneWidget);
    expect(find.text('c6'), findsOneWidget);
    expect(tester.getSize(find.byType(AspectRatio).first).width, greaterThan(300));
  });

  testWidgets('Tocar una pieza propia pide las jugadas legales y resalta sin romper el layout', (tester) async {
    ChessApi.instancia = _ApiFalsa();
    await _montar(tester, fisico: const Size(1206, 2622), dpr: 3.0);

    await tester.tap(find.text('♙').at(4)); // peón de e2 (fila 7, columna e)
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(tester.takeException(), isNull);
    expect(find.text('♔'), findsOneWidget);
  });

  testWidgets('Sin backend dibuja el tablero inicial y muestra el error', (tester) async {
    ChessApi.instancia = _ApiCaida();
    await _montar(tester, fisico: const Size(1206, 2622), dpr: 3.0);

    expect(tester.takeException(), isNull);
    expect(find.text('♙'), findsNWidgets(8));
    expect(find.textContaining('sin backend'), findsOneWidget);
  });

  testWidgets('En una pantalla chica y ancha el tablero se achica en vez de desbordar', (tester) async {
    ChessApi.instancia = _ApiFalsa();
    await _montar(tester, fisico: const Size(800, 600), dpr: 1.0);

    expect(tester.takeException(), isNull);
    expect(find.text('♔'), findsOneWidget);
  });

  testWidgets('La barra de evaluación aparece con retroalimentación en vivo', (tester) async {
    ChessApi.instancia = _ApiFalsa(); // analizarPosicion devuelve: blanco +0.4 peones
    await _montar(tester, fisico: const Size(1206, 2622), dpr: 3.0);

    expect(tester.takeException(), isNull);
    expect(find.text('+0.4'), findsOneWidget);
  });

  testWidgets('Sin retroalimentación en vivo la barra no se dibuja', (tester) async {
    ChessApi.instancia = _ApiFalsa();
    tester.view.physicalSize = const Size(1206, 2622);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.lightTheme,
      home: const GameScreen(
        partidaId: 'p1',
        opponent: OpponentType.stockfish,
        level: 5,
        enableFeedback: false,
      ),
    ));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(tester.takeException(), isNull);
    expect(find.text('+0.4'), findsNothing);
  });
}
