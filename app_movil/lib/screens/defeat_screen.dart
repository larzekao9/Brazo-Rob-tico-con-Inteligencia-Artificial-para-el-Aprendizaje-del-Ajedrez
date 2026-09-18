import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../widgets.dart';

class DefeatScreen extends StatelessWidget {
  final String playerName;
  final int accuracy;
  final int moves;
  final double finalEval;
  final String opponent;

  const DefeatScreen({
    super.key,
    required this.playerName,
    required this.accuracy,
    required this.moves,
    required this.finalEval,
    required this.opponent,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _TopBar(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(AppSpacing.margin),
                child: Column(
                  children: [
                    _HeroSection(playerName: playerName, opponent: opponent),
                    const SizedBox(height: AppSpacing.spaceLg),
                    _MetricsRow(
                      accuracy: accuracy,
                      moves: moves,
                      finalEval: finalEval,
                    ),
                    const SizedBox(height: AppSpacing.spaceLg),
                    _GameEvolutionChart(finalEval: finalEval),
                    const SizedBox(height: AppSpacing.spaceLg),
                    _AdviceBox(),
                    const SizedBox(height: AppSpacing.spaceXl),
                  ],
                ),
              ),
            ),
            _BottomActions(),
          ],
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.chevron_left, color: AppColors.onSurface),
          ),
        ],
      ),
    );
  }
}

class _HeroSection extends StatelessWidget {
  final String playerName;
  final String opponent;

  const _HeroSection({required this.playerName, required this.opponent});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          width: 140,
          height: 140,
          child: CustomPaint(
            painter: _DefeatIllustrationPainter(),
            child: const SizedBox.expand(),
          ),
        ),
        const SizedBox(height: AppSpacing.spaceMd),
        Text(
          '¡Buen intento!',
          style: AppTextStyles.displayLgMobile.copyWith(
            color: AppColors.onSurface,
          ),
        ),
        const SizedBox(height: AppSpacing.spaceSm),
        Text(
          'En esta partida ganó $opponent.',
          style: AppTextStyles.bodyLg.copyWith(
            color: AppColors.onSurface,
            fontWeight: FontWeight.w600,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.spaceSm),
        Text(
          'Cada partida es una oportunidad para aprender y mejorar.',
          style: AppTextStyles.bodySm.copyWith(
            color: AppColors.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.spaceMd),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.spaceLg,
            vertical: AppSpacing.spaceSm,
          ),
          decoration: BoxDecoration(
            color: AppColors.moveMistake.withOpacity(0.1),
            borderRadius: AppRadius.radiusXl,
            border: Border.all(color: AppColors.moveMistake.withOpacity(0.3)),
          ),
          child: Column(
            children: [
              Text(
                '“Las derrotas también forman parte del progreso.”',
                style: AppTextStyles.bodySm.copyWith(
                  color: AppColors.moveMistake,
                  fontStyle: FontStyle.italic,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Container(
                width: 32,
                height: 1.5,
                color: AppColors.moveMistake.withOpacity(0.5),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DefeatIllustrationPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final centerX = size.width / 2;
    final centerY = size.height / 2 + 10;

    // Black king standing (victor)
    _drawKing(canvas, centerX - 35, centerY - 10, const Color(0xFF1E293B), true);

    // White king fallen (defeated)
    canvas.save();
    canvas.translate(centerX + 35, centerY + 20);
    canvas.rotate(-0.8); // Fallen angle
    _drawKing(canvas, 0, 0, const Color(0xFFF8FAFC), false);
    canvas.restore();

    // Quote on right
    final textPainter = TextPainter(
      text: TextSpan(
        text: '“Las derrotas también\nforman parte del progreso.”',
        style: AppTextStyles.labelSm.copyWith(
          color: AppColors.onSurfaceVariant,
          fontStyle: FontStyle.italic,
          fontSize: 8,
        ),
      ),
      textDirection: TextDirection.ltr,
      textAlign: TextAlign.right,
    );
    textPainter.layout(maxWidth: 70);
    textPainter.paint(
      canvas,
      Offset(size.width - 70, centerY - 40),
    );

    // Divider
    final dividerPaint = Paint()
      ..color = AppColors.outlineVariant.withOpacity(0.5)
      ..strokeWidth = 1.5;
    canvas.drawLine(
      Offset(size.width - 30, centerY - 25),
      Offset(size.width - 10, centerY - 25),
      dividerPaint,
    );
  }

  void _drawKing(Canvas canvas, double x, double y, Color color, bool upright) {
    final paint = Paint()..color = color;
    final strokePaint = Paint()
      ..color = const Color(0xFFE2E8F0)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    final scale = 0.7;
    final cx = x;
    final cy = y;

    // Crown cross
    final crossPaint = Paint()
      ..color = upright ? const Color(0xFFCBD5E1) : const Color(0xFF94A3B8)
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(
      Offset(cx - 4 * scale, cy - 28 * scale),
      Offset(cx + 4 * scale, cy - 28 * scale),
      crossPaint,
    );
    canvas.drawLine(
      Offset(cx, cy - 32 * scale),
      Offset(cx, cy - 24 * scale),
      crossPaint,
    );

    // Crown top
    final crownPath = Path()
      ..moveTo(cx - 12 * scale, cy - 20 * scale)
      ..quadraticBezierTo(cx - 12 * scale, cy - 25 * scale, cx, cy - 25 * scale)
      ..quadraticBezierTo(cx + 12 * scale, cy - 25 * scale, cx + 12 * scale, cy - 20 * scale)
      ..lineTo(cx + 10 * scale, cy - 13 * scale)
      ..quadraticBezierTo(cx + 8 * scale, cy - 18 * scale, cx, cy - 18 * scale)
      ..quadraticBezierTo(cx - 8 * scale, cy - 18 * scale, cx - 10 * scale, cy - 13 * scale)
      ..close();
    canvas.drawPath(crownPath, paint);
    canvas.drawPath(crownPath, strokePaint);

    // Neck rings
    canvas.drawOval(
      Rect.fromCenter(center: Offset(cx, cy - 10 * scale), width: 14 * scale, height: 3 * scale),
      strokePaint,
    );
    canvas.drawOval(
      Rect.fromCenter(center: Offset(cx, cy - 6 * scale), width: 12 * scale, height: 2.5 * scale),
      paint,
    );

    // Body
    final bodyPath = Path()
      ..moveTo(cx - 10 * scale, cy - 4 * scale)
      ..quadraticBezierTo(cx - 8 * scale, cy + 15 * scale, cx - 14 * scale, cy + 25 * scale)
      ..lineTo(cx + 14 * scale, cy + 25 * scale)
      ..quadraticBezierTo(cx + 8 * scale, cy + 15 * scale, cx + 10 * scale, cy - 4 * scale)
      ..close();
    canvas.drawPath(bodyPath, paint);
    canvas.drawPath(bodyPath, strokePaint);

    // Pedestal
    canvas.drawOval(
      Rect.fromCenter(center: Offset(cx, cy + 25 * scale), width: 22 * scale, height: 5 * scale),
      strokePaint,
    );
    final pedestalPath = Path()
      ..moveTo(cx - 18 * scale, cy + 27 * scale)
      ..lineTo(cx - 16 * scale, cy + 34 * scale)
      ..lineTo(cx + 16 * scale, cy + 34 * scale)
      ..lineTo(cx + 18 * scale, cy + 27 * scale)
      ..close();
    canvas.drawPath(pedestalPath, paint);
    canvas.drawOval(
      Rect.fromCenter(center: Offset(cx, cy + 34 * scale), width: 27 * scale, height: 6 * scale),
      strokePaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _MetricsRow extends StatelessWidget {
  final int accuracy;
  final int moves;
  final double finalEval;

  const _MetricsRow({
    required this.accuracy,
    required this.moves,
    required this.finalEval,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Row(
        children: [
          _MetricColumn(
            icon: Icons.radio_button_checked,
            iconColor: AppColors.moveMistake,
            label: 'Precisión',
            value: '$accuracy%',
            delta: '-8% vs. tu promedio',
            deltaColor: AppColors.moveBlunder,
          ),
          _MetricDivider(),
          _MetricColumn(
            icon: Icons.bar_chart,
            iconColor: AppColors.onSurfaceVariant,
            label: 'Movimientos',
            value: '$moves',
            delta: 'jugadas',
            deltaColor: AppColors.onSurfaceVariant,
          ),
          _MetricDivider(),
          _MetricColumn(
            icon: Icons.star_outline,
            iconColor: AppColors.onSurfaceVariant,
            label: 'Evaluación final',
            value: finalEval > 0 ? '+${finalEval.toStringAsFixed(1)}' : finalEval.toStringAsFixed(1),
            delta: 'Ventaja clara para negras',
            deltaColor: AppColors.onSurfaceVariant,
          ),
        ],
      ),
    );
  }
}

class _MetricColumn extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final String delta;
  final Color deltaColor;

  const _MetricColumn({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    required this.delta,
    required this.deltaColor,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(AppSpacing.spaceSm),
            decoration: BoxDecoration(
              color: iconColor.withOpacity(0.15),
              borderRadius: AppRadius.radiusMd,
            ),
            child: Icon(icon, color: iconColor, size: 22),
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          Text(
            label,
            style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: AppTextStyles.headlineMd.copyWith(color: AppColors.onSurface),
          ),
          const SizedBox(height: 2),
          Text(
            delta,
            style: AppTextStyles.labelSm.copyWith(
              color: deltaColor,
              fontSize: 9,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _MetricDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 64,
      width: 1,
      color: AppColors.outlineVariant,
    );
  }
}

class _GameEvolutionChart extends StatelessWidget {
  final double finalEval;

  const _GameEvolutionChart({required this.finalEval});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Evolución de la partida',
                style: AppTextStyles.headlineSm.copyWith(color: AppColors.onSurface),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.spaceMd,
                  vertical: AppSpacing.spaceXs,
                ),
                decoration: BoxDecoration(
                  color: AppColors.moveBlunder.withOpacity(0.1),
                  borderRadius: AppRadius.radiusMd,
                  border: Border.all(color: AppColors.moveBlunder.withOpacity(0.3)),
                ),
                child: Column(
                  children: [
                    Text(
                      'Derrota',
                      style: AppTextStyles.labelSm.copyWith(
                        color: AppColors.moveBlunder,
                        fontSize: 9,
                      ),
                    ),
                    Text(
                      finalEval.toStringAsFixed(1),
                      style: AppTextStyles.labelMd.copyWith(
                        color: AppColors.moveBlunder,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceLg),
          SizedBox(
            height: 100,
            child: CustomPaint(
              painter: _DefeatChartPainter(finalEval: finalEval),
              child: const SizedBox.expand(),
            ),
          ),
        ],
      ),
    );
  }
}

class _DefeatChartPainter extends CustomPainter {
  final double finalEval;

  _DefeatChartPainter({required this.finalEval});

  @override
  void paint(Canvas canvas, Size size) {
    // Green area (initial advantage)
    final greenPath = Path();
    greenPath.moveTo(0, size.height * 0.45);
    final greenPoints = [
      (0.0, 0.45), (0.04, 0.45), (0.09, 0.35), (0.14, 0.3), (0.18, 0.32),
      (0.23, 0.3), (0.27, 0.32), (0.31, 0.31), (0.34, 0.42),
    ];
    for (final p in greenPoints) {
      greenPath.lineTo(size.width * p.$1, size.height * p.$2);
    }
    greenPath.lineTo(size.width * 0.34, size.height);
    greenPath.lineTo(0, size.height);
    greenPath.close();

    final greenFill = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0x4010B981), Color(0x0510B981)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
    canvas.drawPath(greenPath, greenFill);

    // Red area (decline)
    final redPath = Path();
    redPath.moveTo(size.width * 0.34, size.height * 0.42);
    final redPoints = [
      (0.37, 0.39), (0.41, 0.38), (0.45, 0.38), (0.48, 0.43), (0.53, 0.41),
      (0.57, 0.47), (0.62, 0.47), (0.66, 0.53), (0.71, 0.53),
      (0.76, 0.58), (0.80, 0.58), (0.82, 0.62), (0.86, 0.62),
      (0.91, 0.67), (0.96, 0.65), (1.0, 0.65),
    ];
    for (final p in redPoints) {
      redPath.lineTo(size.width * p.$1, size.height * p.$2);
    }
    redPath.lineTo(size.width, size.height);
    redPath.lineTo(size.width * 0.34, size.height);
    redPath.close();

    final redFill = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0x05EF4444), Color(0x48EF4444)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
    canvas.drawPath(redPath, redFill);

    // Green line
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..color = AppColors.primary;

    final greenLine = Path();
    for (final p in [(0.0, 0.45), ...greenPoints]) {
      if (p.$1 == 0) greenLine.moveTo(0, size.height * p.$2);
      else greenLine.lineTo(size.width * p.$1, size.height * p.$2);
    }
    canvas.drawPath(greenLine, paint);

    // Red line
    paint.color = AppColors.moveBlunder;
    final redLine = Path();
    redLine.moveTo(size.width * 0.34, size.height * 0.42);
    for (final p in redPoints) {
      redLine.lineTo(size.width * p.$1, size.height * p.$2);
    }
    canvas.drawPath(redLine, paint);

    // Zero line
    final zeroPaint = Paint()
      ..color = AppColors.outlineVariant
      ..strokeWidth = 1;
    canvas.drawLine(
      Offset(0, size.height * 0.45),
      Offset(size.width, size.height * 0.45),
      zeroPaint,
    );

    // Grid lines
    final gridPaint = Paint()
      ..color = AppColors.outlineVariant.withOpacity(0.3)
      ..strokeWidth = 0.5;
    for (int i = 1; i <= 7; i++) {
      final x = size.width * i / 7;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }

    // Labels
    final textPainter = TextPainter(textDirection: TextDirection.ltr);
    textPainter.text = TextSpan(
      text: '+3',
      style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant, fontSize: 9),
    );
    textPainter.layout();
    textPainter.paint(canvas, Offset(4, 4));

    textPainter.text = TextSpan(
      text: '0',
      style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant, fontSize: 9),
    );
    textPainter.layout();
    textPainter.paint(canvas, Offset(4, size.height * 0.45 - textPainter.height / 2));

    textPainter.text = TextSpan(
      text: '-3',
      style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant, fontSize: 9),
    );
    textPainter.layout();
    textPainter.paint(canvas, Offset(4, size.height - textPainter.height - 4));

    // Endpoint dot
    final dotPaint = Paint()..color = AppColors.moveBlunder;
    canvas.drawCircle(
      Offset(size.width, size.height * 0.65),
      5,
      dotPaint,
    );
    canvas.drawCircle(
      Offset(size.width, size.height * 0.65),
      5,
      Paint()..color = Colors.white..style = PaintingStyle.stroke..strokeWidth = 1.5,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _AdviceBox extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.moveBlunder,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColors.moveBlunder.withOpacity(0.3),
                  blurRadius: 8,
                  spreadRadius: 0,
                ),
              ],
            ),
            child: const Icon(
              Icons.lightbulb_outline,
              color: AppColors.onPrimary,
              size: 18,
            ),
          ),
          const SizedBox(width: AppSpacing.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Para mejorar:',
                  style: AppTextStyles.labelMd.copyWith(
                    color: AppColors.moveBlunder,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: AppSpacing.spaceXs),
                Text(
                  'Revisa el momento donde la evaluación cambió drásticamente. '
                  'Probablemente fue un error táctico o una inexactitud posicional. '
                  'Practica puzzles de táctica para agudizar tu visión.',
                  style: AppTextStyles.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BottomActions extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () => context.go('/home'),
              icon: const Icon(Icons.home_outlined),
              label: const Text('Inicio'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.spaceMd),
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.spaceMd),
          Expanded(
            child: FilledButton.icon(
              onPressed: () => context.go('/config'),
              icon: const Icon(Icons.replay),
              label: const Text('Reintentar'),
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.spaceMd),
                backgroundColor: AppColors.moveBlunder,
              ),
            ),
          ),
        ],
      ),
    );
  }
}