import 'package:flutter/material.dart';

import '../../models/learning/learning_models.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_shadows.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import 'chapter_symbol.dart';

/// Banner destacado de la unidad en curso (con badge "EN PROGRESO").
///
/// Dinámico: se alimenta de [LearningUnit], no de strings hardcodeados.
class LearningPathUnitBanner extends StatelessWidget {
  final LearningUnit unit;

  const LearningPathUnitBanner({super.key, required this.unit});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.surfaceContainerHigh,
        borderRadius: AppRadius.radiusXl,
        boxShadow: AppShadows.level1,
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.spaceLg),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _StatusBadge(label: unit.badgeLabel),
                  const SizedBox(height: AppSpacing.spaceXs + 2),
                  Text(
                    unit.title,
                    style: AppTextStyles.headlineSm.copyWith(
                      color: AppColors.onSurface,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.spaceXs),
                  Row(
                    children: [
                      const Icon(
                        Icons.psychology,
                        size: 16,
                        color: AppColors.secondary,
                      ),
                      const SizedBox(width: AppSpacing.spaceXs + 2),
                      Expanded(
                        child: Text(
                          unit.description,
                          style: AppTextStyles.bodySm.copyWith(
                            color: AppColors.onSurfaceVariant,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.spaceMd),
            Container(
              width: 48,
              height: 48,
              decoration: const BoxDecoration(
                color: AppColors.surfaceContainerLowest,
                borderRadius: AppRadius.radiusXl,
                boxShadow: AppShadows.level1,
              ),
              child: Center(
                child: ChapterSymbolIcon(
                  symbol: unit.symbol,
                  color: AppColors.primary,
                  size: 28,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String label;

  const _StatusBadge({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.spaceSm,
        vertical: AppSpacing.spaceXs,
      ),
      decoration: const BoxDecoration(
        color: AppColors.surfaceContainerLowest,
        borderRadius: AppRadius.radiusFull,
        boxShadow: AppShadows.level0,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: const BoxDecoration(
              color: AppColors.primary,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: AppSpacing.spaceXs + 2),
          Text(
            label,
            style: AppTextStyles.labelSm.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}