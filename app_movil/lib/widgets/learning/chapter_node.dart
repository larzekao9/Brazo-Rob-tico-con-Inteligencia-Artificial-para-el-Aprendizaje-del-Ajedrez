import 'package:flutter/material.dart';

import '../../models/learning/learning_models.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_shadows.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import 'chapter_symbol.dart';

/// Nodo circular del camino (con su badge de estado y etiquetas).
///
/// Dinámico: el aspecto completo depende de `ResolvedChapter` (capítulo +
/// estado derivado por el servicio), así que el mismo widget sirve para
/// nodos completados, en curso, disponibles, bloqueados y el "jefe" final.
class ChapterNode extends StatelessWidget {
  final ResolvedChapter resolved;
  final VoidCallback? onTap;

  const ChapterNode({super.key, required this.resolved, this.onTap});

  @override
  Widget build(BuildContext context) {
    final c = resolved.chapter;
    final status = resolved.status;
    final titleColor = status == ChapterStatus.locked
        ? AppColors.onSurfaceVariant
        : AppColors.onSurface;
    final subtitleColor = switch (status) {
      ChapterStatus.completed => AppColors.primary,
      ChapterStatus.inProgress => AppColors.secondary,
      ChapterStatus.available => AppColors.secondary,
      ChapterStatus.locked => AppColors.outline,
    };

    final node = Opacity(
      opacity: status == ChapterStatus.locked ? 0.72 : 1,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _NodeCircle(resolved: resolved, onTap: onTap),
          SizedBox(height: status == ChapterStatus.inProgress ? AppSpacing.spaceMd + 2 : AppSpacing.spaceLg),
          Text(
            c.title,
            textAlign: TextAlign.center,
            style: AppTextStyles.headlineSm.copyWith(color: titleColor),
          ),
          const SizedBox(height: 2),
          Text(
            c.subtitle,
            textAlign: TextAlign.center,
            style: AppTextStyles.telemetrySm.copyWith(
              color: subtitleColor,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );

    return onTap != null
        ? InkWell(borderRadius: AppRadius.radiusLg, onTap: onTap, child: node)
        : node;
  }
}

class _NodeCircle extends StatelessWidget {
  final ResolvedChapter resolved;
  final VoidCallback? onTap;

  const _NodeCircle({required this.resolved, this.onTap});

  @override
  Widget build(BuildContext context) {
    final c = resolved.chapter;
    final status = resolved.status;

    if (c.isBoss) return _buildBoss(status);

    final size = status == ChapterStatus.inProgress ? 80.0 : 64.0;
    final hero = status == ChapterStatus.inProgress;

    final (Color bg, Color fg, Color? border, List<BoxShadow> shadows) =
        switch (status) {
      ChapterStatus.completed => (
          AppColors.primaryFixed,
          AppColors.onPrimaryFixed,
          null,
          const [
            BoxShadow(
              color: Color(0x2E006446),
              blurRadius: 14,
              spreadRadius: -2,
              offset: Offset(0, 4),
            ),
          ],
        ),
      ChapterStatus.inProgress => (
          AppColors.primary,
          AppColors.onPrimary,
          null,
          const [
            BoxShadow(
              color: Color(0x59006446),
              blurRadius: 24,
              spreadRadius: -4,
              offset: Offset(0, 8),
            ),
          ],
        ),
      ChapterStatus.available => (
          AppColors.surfaceContainerLowest,
          AppColors.secondary,
          AppColors.outlineVariant,
          const [
            BoxShadow(
              color: Color(0x1F006875),
              blurRadius: 14,
              spreadRadius: -2,
              offset: Offset(0, 4),
            ),
          ],
        ),
      ChapterStatus.locked => (
          AppColors.surfaceContainerLow,
          AppColors.outline,
          null,
          const [],
        ),
    };

    final circle = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: bg,
        shape: BoxShape.circle,
        border: border != null ? Border.all(color: border) : null,
        boxShadow: shadows,
      ),
      child: Center(
        child: ChapterSymbolIcon(
          symbol: c.symbol,
          color: fg,
          size: size * 0.47,
        ),
      ),
    );

    return Stack(
      alignment: Alignment.center,
      children: [
        if (hero) _HeroAuraRings(size: size),
        SizedBox(width: size, height: size, child: circle),
        Positioned(top: -4, right: -4, child: _StatusBadgeBox(status)),
      ],
    );
  }

  Widget _buildBoss(ChapterStatus status) {
    final locked = status == ChapterStatus.locked;
    return Stack(
      clipBehavior: Clip.none,
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: locked
                ? AppColors.surfaceContainerLow
                : AppColors.tertiaryContainer,
            borderRadius: BorderRadius.circular(AppRadius.lg + 4),
            boxShadow: locked
                ? AppShadows.level2
                : AppShadows.neuralAmberGlow(radius: 20),
          ),
          child: Center(
            child: ChapterSymbolIcon(
              symbol: ChapterSymbol.trophy,
              color: locked ? AppColors.tertiary : AppColors.onTertiaryContainer,
              size: 36,
            ),
          ),
        ),
        Positioned(
          top: -8,
          right: -8,
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.spaceSm - 2,
              vertical: 3,
            ),
            decoration: const BoxDecoration(
              color: AppColors.surfaceContainerHighest,
              borderRadius: AppRadius.radiusFull,
              boxShadow: AppShadows.level1,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  locked ? Icons.lock : Icons.lock_open,
                  size: 12,
                  color: AppColors.onSurfaceVariant,
                ),
                const SizedBox(width: 3),
                Text(
                  'FINAL',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.onSurfaceVariant,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _HeroAuraRings extends StatelessWidget {
  final double size;

  const _HeroAuraRings({required this.size});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Container(
            width: size + 24,
            height: size + 24,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primaryContainer.withValues(alpha: 0.18),
            ),
          ),
          Container(
            width: size + 12,
            height: size + 12,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: AppColors.secondaryContainer.withValues(alpha: 0.5),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusBadgeBox extends StatelessWidget {
  final ChapterStatus status;

  const _StatusBadgeBox(this.status);

  @override
  Widget build(BuildContext context) {
    final (Color bg, IconData icon, Color fg, double size) = switch (status) {
      ChapterStatus.completed => (
          AppColors.primary,
          Icons.check,
          AppColors.onPrimary,
          14.0,
        ),
      ChapterStatus.inProgress => (
          AppColors.secondaryContainer,
          Icons.play_arrow,
          AppColors.onSecondaryContainer,
          16.0,
        ),
      ChapterStatus.available => (
          AppColors.secondaryFixed,
          Icons.lock_open,
          AppColors.onSecondaryFixed,
          14.0,
        ),
      ChapterStatus.locked => (
          AppColors.surfaceContainerHigh,
          Icons.lock,
          AppColors.outline,
          13.0,
        ),
    };

    return Container(
      width: size + 10,
      height: size + 10,
      decoration: BoxDecoration(
        color: bg,
        shape: BoxShape.circle,
        boxShadow: AppShadows.level1,
      ),
      child: Icon(icon, size: size, color: fg),
    );
  }
}

/// Tarjeta expandida del capítulo en curso (hero node), con su CTA.
class ActiveChapterCard extends StatelessWidget {
  final ResolvedChapter resolved;
  final VoidCallback onContinue;

  const ActiveChapterCard({
    super.key,
    required this.resolved,
    required this.onContinue,
  });

  @override
  Widget build(BuildContext context) {
    final c = resolved.chapter;
    final total = c.stepsTotal;
    final done = resolved.stepsDone.clamp(0, total);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      decoration: const BoxDecoration(
        color: AppColors.surfaceContainerLowest,
        borderRadius: AppRadius.radiusXl,
        boxShadow: [
          BoxShadow(
            color: Color(0x0F0B1C30),
            blurRadius: 20,
            spreadRadius: -6,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.spaceSm + 2,
                    vertical: 3,
                  ),
                  decoration: const BoxDecoration(
                    color: AppColors.surfaceContainerHigh,
                    borderRadius: AppRadius.radiusFull,
                  ),
                  child: Text(
                    'EN CURSO • LECCIÓN $done DE $total',
                    style: AppTextStyles.labelSm.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.bold,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.spaceSm),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.bolt, size: 16, color: AppColors.secondary),
                  const SizedBox(width: 2),
                  Text(
                    '+${c.xp} XP',
                    style: AppTextStyles.telemetrySm.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceMd),
          Text(
            c.title,
            style: AppTextStyles.headlineMd.copyWith(color: AppColors.onSurface),
          ),
          if (c.description != null) ...[
            const SizedBox(height: AppSpacing.spaceXs + 2),
            Text(
              c.description!,
              style: AppTextStyles.bodyMd.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.spaceMd + 2),
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: AppRadius.radiusFull,
                  child: LinearProgressIndicator(
                    value: total > 0 ? done / total : 0,
                    minHeight: 6,
                    backgroundColor: AppColors.surfaceContainer,
                    valueColor: const AlwaysStoppedAnimation<Color>(
                      AppColors.primary,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.spaceMd),
              Text(
                '$done/$total pasos',
                style: AppTextStyles.telemetrySm.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceLg),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton.icon(
              onPressed: onContinue,
              icon: const Icon(Icons.arrow_forward, size: 20),
              label: const Text('Continuar Lección'),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primaryContainer,
                foregroundColor: AppColors.onPrimaryContainer,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.base + 2),
                ),
                textStyle: AppTextStyles.headlineSm.copyWith(
                  color: AppColors.onPrimaryContainer,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}