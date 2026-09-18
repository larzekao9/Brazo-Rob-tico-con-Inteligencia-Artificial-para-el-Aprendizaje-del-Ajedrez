import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../theme.dart';

/// Curva de cómo cambió la evaluación real de Stockfish a lo largo de la
/// partida — valores positivos favorecen a blancas, negativos a negras.
class EvaluationHistoryChart extends StatelessWidget {
  final List<double> valores;

  const EvaluationHistoryChart({super.key, required this.valores});

  @override
  Widget build(BuildContext context) {
    if (valores.length < 2) {
      return SizedBox(
        height: 120,
        child: Center(
          child: Text(
            'Jugá para ver la curva',
            style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
          ),
        ),
      );
    }

    final maxAbs = valores.fold<double>(3, (acc, v) => v.abs() > acc ? v.abs() : acc);
    final tope = maxAbs.clamp(3, 12).ceilToDouble();
    final ultimoValor = valores.last;
    final colorCurva = ultimoValor >= 0 ? AppColors.primary : AppColors.moveMistake;

    final puntos = [
      for (var i = 0; i < valores.length; i++) FlSpot(i.toDouble(), valores[i].clamp(-tope, tope)),
    ];

    return SizedBox(
      height: 160,
      child: LineChart(
        LineChartData(
          minY: -tope,
          maxY: tope,
          minX: 0,
          maxX: (valores.length - 1).toDouble(),
          gridData: FlGridData(
            horizontalInterval: tope,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => FlLine(color: AppColors.outlineVariant, strokeWidth: 1),
          ),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 32,
                interval: tope,
                getTitlesWidget: (value, meta) => Text(
                  value > 0 ? '+${value.toInt()}' : '${value.toInt()}',
                  style: AppTextStyles.telemetrySm.copyWith(color: AppColors.onSurfaceVariant),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 22,
                interval: (valores.length - 1) == 0 ? 1 : (valores.length - 1).toDouble(),
                getTitlesWidget: (value, meta) {
                  final texto = value == 0 ? 'Inicio' : (value.round() == valores.length - 1 ? 'Movimientos' : '');
                  return Text(texto, style: AppTextStyles.telemetrySm.copyWith(color: AppColors.onSurfaceVariant));
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: puntos,
              isCurved: false,
              barWidth: 2,
              color: colorCurva,
              belowBarData: BarAreaData(show: true, color: colorCurva.withOpacity(0.12)),
              dotData: FlDotData(
                show: true,
                checkToShowDot: (spot, _) => spot.x == puntos.last.x,
                getDotPainter: (spot, percent, bar, index) =>
                    FlDotCirclePainter(radius: 5, color: colorCurva, strokeWidth: 2, strokeColor: AppColors.surfaceContainerLowest),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
