import 'package:flutter/material.dart';
import '../theme.dart';
import '../models.dart';

class MoveHistory extends StatelessWidget {
  final List<MoveEntry> moves;
  final int? highlightedIndex;
  final void Function(int index)? onMoveTap;

  const MoveHistory({
    super.key,
    required this.moves,
    this.highlightedIndex,
    this.onMoveTap,
  });

  /// Alto fijo del carrusel: un `ListView` horizontal no puede vivir en una
  /// columna sin alto acotado (en release la fila colapsa todo lo demás).
  static const double alto = 72;

  @override
  Widget build(BuildContext context) {
    if (moves.isEmpty) {
      return SizedBox(
        height: alto,
        child: Center(
          child: Text(
            'Sin jugadas aún',
            style: AppTextStyles.bodyMd.copyWith(
              color: AppColors.onSurfaceVariant,
            ),
          ),
        ),
      );
    }

    return SizedBox(
      height: alto,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.spaceMd,
          vertical: AppSpacing.spaceSm,
        ),
        itemCount: moves.length,
        separatorBuilder: (_, __) => const SizedBox(width: AppSpacing.spaceSm),
        itemBuilder: (context, index) {
          final move = moves[index];
          final isHighlighted = index == highlightedIndex;
          return _MoveChip(
            move: move,
            index: index,
            isHighlighted: isHighlighted,
            onTap: onMoveTap != null ? () => onMoveTap!(index) : null,
          );
        },
      ),
    );
  }
}

class MoveEntry {
  final int moveNumber;
  final String whiteMove;
  final String? blackMove;
  final MoveQuality? whiteQuality;
  final MoveQuality? blackQuality;
  final double? whiteEval;
  final double? blackEval;

  const MoveEntry({
    required this.moveNumber,
    required this.whiteMove,
    this.blackMove,
    this.whiteQuality,
    this.blackQuality,
    this.whiteEval,
    this.blackEval,
  });
}

class _MoveChip extends StatelessWidget {
  final MoveEntry move;
  final int index;
  final bool isHighlighted;
  final VoidCallback? onTap;

  const _MoveChip({
    required this.move,
    required this.index,
    required this.isHighlighted,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.spaceMd,
          vertical: AppSpacing.spaceSm,
        ),
        decoration: BoxDecoration(
          color: isHighlighted
              ? AppColors.primaryContainer
              : AppColors.surfaceContainerLowest,
          borderRadius: AppRadius.radiusLg,
          border: Border.all(
            color: isHighlighted
                ? AppColors.primary
                : AppColors.outlineVariant,
            width: isHighlighted ? 2 : 1,
          ),
          boxShadow: isHighlighted ? AppShadows.level2 : AppShadows.level1,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${move.moveNumber}.',
              style: AppTextStyles.labelSm.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 2),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _MoveText(
                  text: move.whiteMove,
                  quality: move.whiteQuality,
                ),
                if (move.blackMove != null) ...[
                  const SizedBox(width: AppSpacing.spaceSm),
                  _MoveText(
                    text: move.blackMove!,
                    quality: move.blackQuality,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MoveText extends StatelessWidget {
  final String text;
  final MoveQuality? quality;

  const _MoveText({required this.text, this.quality});

  Color _qualityColor(MoveQuality q) {
    switch (q) {
      case MoveQuality.brilliant:
        return AppColors.moveBrilliant;
      case MoveQuality.best:
        return AppColors.moveBest;
      case MoveQuality.good:
        return AppColors.onSurface;
      case MoveQuality.inaccuracy:
        return AppColors.moveMistake;
      case MoveQuality.mistake:
        return AppColors.moveMistake;
      case MoveQuality.blunder:
        return AppColors.moveBlunder;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = quality != null ? _qualityColor(quality!) : AppColors.onSurface;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          text,
          style: AppTextStyles.telemetryMd.copyWith(
            color: color,
            fontWeight: quality != null ? FontWeight.w600 : FontWeight.w500,
          ),
        ),
        if (quality != null) ...[
          const SizedBox(width: 4),
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
        ],
      ],
    );
  }
}