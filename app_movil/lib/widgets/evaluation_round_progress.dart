import 'package:flutter/material.dart';
import '../theme.dart';
import 'glass_card.dart';

/// "Partida de evaluación X de N" — solo lo usa el diagnóstico ("Mide tu
/// nivel"), que juega varias partidas cortas y promedia la precisión.
class EvaluationRoundProgress extends StatelessWidget {
  final int ronda;
  final int totalRondas;
  final double progreso;
  final double? evaluacionActual;

  const EvaluationRoundProgress({
    super.key,
    required this.ronda,
    required this.totalRondas,
    required this.progreso,
    this.evaluacionActual,
  });

  @override
  Widget build(BuildContext context) {
    final favoreceBlancas = (evaluacionActual ?? 0) >= 0;
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceMd),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Partida de evaluación',
                style: AppTextStyles.labelMd.copyWith(color: AppColors.onSurfaceVariant),
              ),
              Text(
                '$ronda de $totalRondas',
                style: AppTextStyles.labelMd.copyWith(color: AppColors.onSurface, fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: AppRadius.radiusFull,
                  child: LinearProgressIndicator(
                    value: progreso.clamp(0, 1),
                    minHeight: 8,
                    backgroundColor: AppColors.outlineVariant,
                    color: AppColors.primary,
                  ),
                ),
              ),
              if (evaluacionActual != null) ...[
                const SizedBox(width: AppSpacing.spaceSm),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.spaceSm, vertical: 2),
                  decoration: BoxDecoration(
                    color: favoreceBlancas ? AppColors.primaryContainer : AppColors.tertiaryContainer,
                    borderRadius: AppRadius.radiusFull,
                  ),
                  child: Text(
                    evaluacionActual! > 0
                        ? '+${evaluacionActual!.toStringAsFixed(1)}'
                        : evaluacionActual!.toStringAsFixed(1),
                    style: AppTextStyles.labelSm.copyWith(
                      color: favoreceBlancas ? AppColors.primary : AppColors.onTertiaryContainer,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
