import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';

/// Tarjeta resumen de progreso global del camino de aprendizaje.
///
/// Datos: nivel/rango, XP acumulada, barra segmentada y leyenda de
/// capítulos/lecciones. Todo llega por parámetros: es un widget puro.
class LearningPathProgressCard extends StatelessWidget {
  final int nivel;
  final String rankLabel;
  final int xp;
  final int completedChapters;
  final int totalChapters;
  final int pendingLessons;

  /// Fracción completada 0..1 (controla la barra).
  final double fraction;

  const LearningPathProgressCard({
    super.key,
    required this.nivel,
    required this.rankLabel,
    required this.xp,
    required this.completedChapters,
    required this.totalChapters,
    required this.pendingLessons,
    required this.fraction,
  })  : assert(fraction >= 0 && fraction <= 1),
        assert(completedChapters <= totalChapters);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.spaceLg - 2),
      decoration: const BoxDecoration(
        color: AppColors.surfaceContainerLowest,
        borderRadius: AppRadius.radiusXl,
        boxShadow: [
          BoxShadow(
            color: Color(0x0A0B1C30),
            blurRadius: 12,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const _LevelBadge(
                icon: Icons.military_tech,
                accent: AppColors.primary,
              ),
              const SizedBox(width: AppSpacing.spaceMd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Nivel $nivel • $rankLabel',
                      style: AppTextStyles.labelMd.copyWith(
                        color: AppColors.onSurfaceVariant,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      '${(fraction * 100).round()}% completado',
                      style: AppTextStyles.headlineSm.copyWith(
                        color: AppColors.onSurface,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: AppSpacing.spaceSm),
              _XpBadge(xp: xp),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceLg),
          ClipRRect(
            borderRadius: AppRadius.radiusFull,
            child: LinearProgressIndicator(
              value: fraction,
              minHeight: 8,
              backgroundColor: AppColors.surfaceContainer,
              valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
            ),
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  '$completedChapters de $totalChapters capítulos listos',
                  style: AppTextStyles.telemetrySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: AppSpacing.spaceSm),
              Text(
                pendingLessons > 0
                    ? '$pendingLessons lecciones pendientes'
                    : 'Camino completado',
                style: AppTextStyles.telemetrySm.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LevelBadge extends StatelessWidget {
  final IconData icon;
  final Color accent;

  const _LevelBadge({required this.icon, required this.accent});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(AppRadius.base + 1),
      ),
      child: Icon(icon, size: 17, color: accent),
    );
  }
}

class _XpBadge extends StatelessWidget {
  final int xp;

  const _XpBadge({required this.xp});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.spaceSm,
        vertical: AppSpacing.spaceXs,
      ),
      decoration: BoxDecoration(
        color: AppColors.primaryFixed.withValues(alpha: 0.3),
        borderRadius: AppRadius.radiusBase,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.stars, size: 15, color: AppColors.primary),
          const SizedBox(width: 4),
          Text(
            '$xp XP',
            style: AppTextStyles.telemetrySm.copyWith(
              color: AppColors.onPrimaryFixedVariant,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}