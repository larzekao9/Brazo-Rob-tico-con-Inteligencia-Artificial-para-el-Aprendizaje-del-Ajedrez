import 'package:flutter_test/flutter_test.dart';

import 'package:chessia_app/services/partida.dart';

void main() {
  test('EstadisticasUsuario.fromJson parsea la respuesta real de /usuario/estadisticas',
      () {
    final stats = EstadisticasUsuario.fromJson(const {
      'total_partidas': 7,
      'partidas_ganadas': 4,
      'partidas_perdidas': 2,
      'partidas_tablas': 1,
      'win_percent_promedio': 57.14,
      'racha_victoria_actual': 3,
      'precision_promedio': 71.5,
      'top_errores': [
        {'tipo': 'blunder', 'cantidad': 2},
        {'tipo': 'error', 'cantidad': 1},
      ],
    });

    expect(stats.totalPartidas, 7);
    expect(stats.partidasGanadas, 4);
    expect(stats.precisionPromedio, 71.5);
    expect(stats.topErrores, hasLength(2));
    expect(stats.topErrores.first.tipo, 'blunder');
    expect(stats.topErrores.first.cantidad, 2);
  });

  test('EstadisticasUsuario.fromJson tolera top_errores ausente', () {
    final stats = EstadisticasUsuario.fromJson(const {
      'total_partidas': 0,
      'partidas_ganadas': 0,
      'partidas_perdidas': 0,
      'partidas_tablas': 0,
      'win_percent_promedio': 0,
      'racha_victoria_actual': 0,
      'precision_promedio': 0,
    });

    expect(stats.totalPartidas, 0);
    expect(stats.topErrores, isEmpty);
  });

  test('EstadisticasUsuario.fromJson no se rompe sin precision_promedio '
      '(backend desactualizado) y conserva las partidas', () {
    final stats = EstadisticasUsuario.fromJson(const {
      'total_partidas': 5,
      'partidas_ganadas': 3,
      'partidas_perdidas': 1,
      'partidas_tablas': 1,
      'win_percent_promedio': 60,
      'racha_victoria_actual': 2,
    });

    expect(stats.totalPartidas, 5);
    expect(stats.partidasGanadas, 3);
    expect(stats.precisionPromedio, 0.0);
  });
}