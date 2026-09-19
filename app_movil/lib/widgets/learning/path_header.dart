import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_shadows.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';

/// Pill de racha (ej: "3 DÍAS") reutilizable, con fuego ámbar.
class StreakBadge extends StatelessWidget {
  final int days;
  final Color? color;

  const StreakBadge({super.key, required this.days, this.color});

  @override
  Widget build(BuildContext context) {
    final accent = color ?? AppColors.tertiary;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.spaceSm + 2,
        vertical: AppSpacing.spaceXs,
      ),
      decoration: const BoxDecoration(
        color: AppColors.surfaceContainerLow,
        borderRadius: AppRadius.radiusFull,
        boxShadow: AppShadows.level1,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.local_fire_department, size: 18, color: accent),
          const SizedBox(width: AppSpacing.spaceXs + 2),
          Text(
            days >= 0 ? '$days DÍAS' : '—',
            style: AppTextStyles.telemetrySm.copyWith(
              color: AppColors.onSurface,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

/// Cabecera del camino: botón volver + título central + pill de racha.
class LearningPathHeader extends StatelessWidget {
  final String title;
  final String subtitle;
  final int streakDays;
  final VoidCallback onBack;

  const LearningPathHeader({
    super.key,
    required this.title,
    required this.subtitle,
    required this.streakDays,
    required this.onBack,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.margin,
        vertical: AppSpacing.spaceSm,
      ),
      child: Row(
        children: [
          IconButton(
            onPressed: onBack,
            icon: const Icon(Icons.arrow_back, size: 20),
            style: IconButton.styleFrom(
              backgroundColor: AppColors.surfaceContainerLow,
              foregroundColor: AppColors.onSurface,
              shape: const CircleBorder(),
              padding: EdgeInsets.zero,
              minimumSize: const Size(40, 40),
            ),
          ),
          Expanded(
            child: Column(
              children: [
                Text(
                  subtitle.toUpperCase(),
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.primary,
                    letterSpacing: 1.2,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  title,
                  style: AppTextStyles.headlineMd.copyWith(
                    color: AppColors.onSurface,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          StreakBadge(days: streakDays),
        ],
      ),
    );
  }
}