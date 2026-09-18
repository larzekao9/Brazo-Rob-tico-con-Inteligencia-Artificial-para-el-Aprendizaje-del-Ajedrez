import 'package:flutter/material.dart';
import '../theme.dart';

class EvaluationBar extends StatelessWidget {
  final double evaluation;
  final bool isWhitePerspective;
  final double height;
  final double width;

  const EvaluationBar({
    super.key,
    required this.evaluation,
    this.isWhitePerspective = true,
    this.height = 4,
    this.width = double.infinity,
  });

  /// Ancho de respaldo cuando ni `width` ni el padre dan un límite finito
  /// (p. ej. dentro de una fila scrolleable). Evita posiciones infinitas.
  static const double _anchoRespaldo = 200;

  @override
  Widget build(BuildContext context) {
    if (width.isFinite) return _construir(context, width);
    // `width` por defecto es infinito: tomar el ancho real que da el padre.
    return LayoutBuilder(
      builder: (context, constraints) => _construir(
        context,
        constraints.maxWidth.isFinite ? constraints.maxWidth : _anchoRespaldo,
      ),
    );
  }

  Widget _construir(BuildContext context, double width) {
    final theme = Theme.of(context);
    final chessTheme = theme.extension<ChessThemeExtension>()!;

    final double clampedEval = evaluation.clamp(-10.0, 10.0);
    final double whitePercent = isWhitePerspective
        ? (clampedEval + 10) / 20
        : (10 - clampedEval) / 20;

    return SizedBox(
      width: width,
      height: height,
      child: Stack(
        children: [
          Container(
            decoration: BoxDecoration(
              color: chessTheme.blackSquare,
              borderRadius: BorderRadius.circular(height / 2),
            ),
          ),
          FractionallySizedBox(
            widthFactor: whitePercent.clamp(0.0, 1.0),
            child: Container(
              decoration: BoxDecoration(
                color: chessTheme.whiteSquare,
                borderRadius: BorderRadius.circular(height / 2),
              ),
            ),
          ),
          Positioned(
            left: (whitePercent * width).clamp(8.0, width - 8.0) - 8,
            top: (height - 16) / 2,
            child: _EvaluationIndicator(evaluation: evaluation),
          ),
        ],
      ),
    );
  }
}

class _EvaluationIndicator extends StatelessWidget {
  final double evaluation;

  const _EvaluationIndicator({required this.evaluation});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isMate = evaluation.abs() > 9;
    final String text;

    if (isMate) {
      final mateIn = evaluation > 0 ? evaluation.toInt() - 10 : -(evaluation.toInt() + 10);
      text = 'M${mateIn.abs()}';
    } else {
      text = evaluation > 0 ? '+${evaluation.toStringAsFixed(1)}' : evaluation.toStringAsFixed(1);
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerLowest,
        borderRadius: AppRadius.radiusBase,
        border: Border.all(color: AppColors.outline, width: 1),
        boxShadow: AppShadows.level2,
      ),
      child: Text(
        text,
        style: AppTextStyles.telemetrySm.copyWith(
          color: evaluation > 0 ? AppColors.primary : AppColors.onSurface,
        ),
      ),
    );
  }
}

class VerticalEvaluationBar extends StatelessWidget {
  final double evaluation;
  final bool isWhitePerspective;
  final double width;
  final double height;

  const VerticalEvaluationBar({
    super.key,
    required this.evaluation,
    this.isWhitePerspective = true,
    this.width = 12,
    this.height = double.infinity,
  });

  @override
  Widget build(BuildContext context) {
    // `height` por defecto es infinito: hay que resolverlo con el alto real
    // del padre antes de rotar, si no la barra pide un ancho infinito y el
    // layout falla (en release se ve como una zona en blanco).
    return LayoutBuilder(
      builder: (context, constraints) {
        final largo = height.isFinite
            ? height
            : (constraints.maxHeight.isFinite ? constraints.maxHeight : EvaluationBar._anchoRespaldo);
        return RotatedBox(
          quarterTurns: 3,
          child: SizedBox(
            width: largo,
            height: width,
            child: EvaluationBar(
              evaluation: evaluation,
              isWhitePerspective: isWhitePerspective,
              height: width,
              width: largo,
            ),
          ),
        );
      },
    );
  }
}