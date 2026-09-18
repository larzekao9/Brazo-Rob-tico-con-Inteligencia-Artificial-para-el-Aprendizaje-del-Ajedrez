import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../widgets.dart';

class VictoryScreen extends StatelessWidget {
  final String playerName;
  final int accuracy;
  final int moves;
  final double finalEval;
  final String opponent;

  const VictoryScreen({
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
        child: Stack(
          children: [
            _ConfettiBackground(),
            Column(
              children: [
                _TopBar(),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(AppSpacing.margin),
                    child: Column(
                      children: [
                        _TrophyIllustration(),
                        const SizedBox(height: AppSpacing.spaceMd),
                        _TitleSection(playerName: playerName, opponent: opponent),
                        const SizedBox(height: AppSpacing.spaceMd),
                        _QuoteBadge(),
                        const SizedBox(height: AppSpacing.spaceLg),
                        _MetricsRow(
                          accuracy: accuracy,
                          moves: moves,
                          finalEval: finalEval,
                        ),
                        const SizedBox(height: AppSpacing.spaceLg),
                        _GameEvolutionChart(),
                        const SizedBox(height: AppSpacing.spaceXl),
                      ],
                    ),
                  ),
                ),
                _BottomActions(),
              ],
            ),
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

class _ConfettiBackground extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final colors = [
      AppColors.tertiary,
      AppColors.primary,
      AppColors.moveBlunder,
      AppColors.secondary,
    ];

    return Stack(
      children: List.generate(15, (i) {
        return Positioned(
          top: (i * 56) % 800 + 50.0,
          left: (i * 37) % 350 + 20.0,
          child: Transform.rotate(
            angle: (i * 0.5) % 3.14,
            child: Container(
              width: [3, 4, 5, 6][i % 4].toDouble(),
              height: [5, 6, 7, 8][i % 4].toDouble(),
              decoration: BoxDecoration(
                color: colors[i % colors.length].withOpacity(0.8),
                borderRadius: AppRadius.radiusSm,
              ),
            ),
          ),
        );
      }),
    );
  }
}

class _TrophyIllustration extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 160,
      height: 140,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primary.withOpacity(0.15),
            ),
          ),
          CustomPaint(
            size: const Size(140, 120),
            painter: _TrophyPainter(),
          ),
        ],
      ),
    );
  }
}

class _TrophyPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final centerX = size.width / 2;
    final centerY = size.height / 2 + 10;

    // Laurel left
    final laurelPaint = Paint()..color = const Color(0xFF2CB67D);
    final laurelPath = Path()
      ..moveTo(centerX - 20, centerY + 30)
      ..quadraticBezierTo(centerX - 40, centerY + 10, centerX - 30, centerY - 10)
      ..quadraticBezierTo(centerX - 25, centerY + 5, centerX - 15, centerY + 15)
      ..close();
    canvas.drawPath(laurelPath, laurelPaint);

    // Laurel right
    final laurelPathR = Path()
      ..moveTo(centerX + 20, centerY + 30)
      ..quadraticBezierTo(centerX + 40, centerY + 10, centerX + 30, centerY - 10)
      ..quadraticBezierTo(centerX + 25, centerY + 5, centerX + 15, centerY + 15)
      ..close();
    canvas.drawPath(laurelPathR, laurelPaint);

    // Trophy base
    final basePaint = Paint()
      ..shader = const LinearGradient(
        colors: [Color(0xFF8D5B28), Color(0xFFE09939)],
      ).createShader(Rect.fromLTWH(centerX - 26, centerY + 60, 52, 12));
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(centerX - 26, centerY + 60, 52, 12),
        const Radius.circular(3),
      ),
      basePaint,
    );

    // Trophy cup
    final cupPaint = Paint()
      ..shader = const LinearGradient(
        colors: [Color(0xFFFED330), Color(0xFFF39C12), Color(0xFFE67E22)],
      ).createShader(Rect.fromLTWH(centerX - 34, centerY - 30, 68, 84));

    final cupPath = Path()
      ..moveTo(centerX - 34, centerY - 10)
      ..quadraticBezierTo(centerX - 34, centerY - 30, centerX - 26, centerY - 30)
      ..lineTo(centerX + 26, centerY - 30)
      ..quadraticBezierTo(centerX + 34, centerY - 30, centerX + 34, centerY - 10)
      ..quadraticBezierTo(centerX + 34, centerY + 30, centerX, centerY + 60)
      ..quadraticBezierTo(centerX - 34, centerY + 30, centerX - 34, centerY - 10)
      ..close();
    canvas.drawPath(cupPath, cupPaint);

    // Rim
    final rimPaint = Paint()..color = const Color(0xFFFBD24E);
    canvas.drawOval(
      Rect.fromCenter(center: Offset(centerX, centerY - 28), width: 68, height: 14),
      rimPaint,
    );

    // Crown on cup
    final crownPaint = Paint()..color = Colors.white;
    final crownPath = Path()
      ..moveTo(centerX - 10, centerY + 8)
      ..lineTo(centerX - 14, centerY - 6)
      ..lineTo(centerX - 6, centerY - 1)
      ..lineTo(centerX, centerY - 10)
      ..lineTo(centerX + 6, centerY - 1)
      ..lineTo(centerX + 14, centerY - 6)
      ..lineTo(centerX + 10, centerY + 8)
      ..close();
    canvas.drawPath(crownPath, crownPaint);

    // Handles
    final handlePaint = Paint()
      ..color = const Color(0xFFF1A825)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 7
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(
      Path()
        ..moveTo(centerX - 32, centerY)
        ..quadraticBezierTo(centerX - 48, centerY, centerX - 48, centerY + 30)
        ..quadraticBezierTo(centerX - 48, centerY + 45, centerX - 26, centerY + 45),
      handlePaint,
    );
    canvas.drawPath(
      Path()
        ..moveTo(centerX + 32, centerY)
        ..quadraticBezierTo(centerX + 48, centerY, centerX + 48, centerY + 30)
        ..quadraticBezierTo(centerX + 48, centerY + 45, centerX + 26, centerY + 45),
      handlePaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _TitleSection extends StatelessWidget {
  final String playerName;
  final String opponent;

  const _TitleSection({required this.playerName, required this.opponent});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          '¡Ganaste!',
          style: AppTextStyles.displayLgMobile.copyWith(
            color: AppColors.onSurface,
          ),
        ),
        const SizedBox(height: AppSpacing.spaceSm),
        Text(
          'Muy buen trabajo, $playerName',
          style: AppTextStyles.bodyLg.copyWith(
            color: AppColors.onSurface,
            fontWeight: FontWeight.w600,
          ),
        ),
        Text(
          'Has vencido a $opponent',
          style: AppTextStyles.bodySm.copyWith(
            color: AppColors.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

class _QuoteBadge extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.spaceLg,
        vertical: AppSpacing.spaceSm,
      ),
      decoration: BoxDecoration(
        color: AppColors.primaryContainer,
        borderRadius: AppRadius.radiusXl,
      ),
      child: Text(
        '“La constancia te lleva más lejos.”',
        style: AppTextStyles.labelSm.copyWith(
          color: AppColors.primary,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
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
            iconColor: AppColors.primary,
            label: 'Precisión',
            value: '$accuracy%',
            delta: '+12% vs. tu promedio',
            deltaColor: AppColors.primary,
          ),
          _MetricDivider(),
          _MetricColumn(
            icon: Icons.bar_chart,
            iconColor: AppColors.secondary,
            label: 'Movimientos',
            value: '$moves',
            delta: 'jugadas',
            deltaColor: AppColors.onSurfaceVariant,
          ),
          _MetricDivider(),
          _MetricColumn(
            icon: Icons.star_outline,
            iconColor: AppColors.tertiary,
            label: 'Evaluación final',
            value: finalEval > 0 ? '+${finalEval.toStringAsFixed(1)}' : finalEval.toStringAsFixed(1),
            delta: 'Ventaja clara para blancas',
            deltaColor: AppColors.primary,
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
                  gradient: LinearGradient(
                    colors: [AppColors.primary, AppColors.primary.withOpacity(0.8)],
                  ),
                  borderRadius: AppRadius.radiusMd,
                ),
                child: Column(
                  children: [
                    Text('Victoria', style: AppTextStyles.labelSm.copyWith(color: AppColors.onPrimary, fontSize: 9)),
                    Text('+2.3', style: AppTextStyles.labelMd.copyWith(color: AppColors.onPrimary, fontSize: 12)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceLg),
          SizedBox(
            height: 100,
            child: CustomPaint(
              painter: _VictoryChartPainter(),
              child: const SizedBox.expand(),
            ),
          ),
        ],
      ),
    );
  }
}

class _VictoryChartPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    // Green area (advantage)
    final greenPath = Path();
    greenPath.moveTo(0, size.height * 0.4);
    final greenPoints = [
      (0.0, 0.4), (0.04, 0.4), (0.09, 0.35), (0.14, 0.3), (0.18, 0.32),
      (0.23, 0.3), (0.27, 0.32), (0.31, 0.31), (0.35, 0.4),
    ];
    for (final p in greenPoints) {
      greenPath.lineTo(size.width * p.$1, size.height * p.$2);
    }
    greenPath.lineTo(size.width * 0.35, size.height);
    greenPath.lineTo(0, size.height);
    greenPath.close();

    final greenFill = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0x4010B981), Color(0x0510B981)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
    canvas.drawPath(greenPath, greenFill);

    // Red area (disadvantage - opponent)
    final redPath = Path();
    redPath.moveTo(size.width * 0.35, size.height * 0.4);
    final redPoints = [
      (0.37, 0.39), (0.41, 0.34), (0.45, 0.38), (0.48, 0.43), (0.53, 0.41),
      (0.57, 0.47), (0.62, 0.47), (0.66, 0.53), (0.71, 0.56),
      (0.76, 0.62), (0.80, 0.62), (0.82, 0.67), (0.86, 0.65),
      (0.91, 0.66), (0.96, 0.69), (1.0, 0.7),
    ];
    for (final p in redPoints) {
      redPath.lineTo(size.width * p.$1, size.height * p.$2);
    }
    redPath.lineTo(size.width, size.height);
    redPath.lineTo(size.width * 0.35, size.height);
    redPath.close();

    final redFill = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0x05EF4444), Color(0x48EF4444)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
    canvas.drawPath(redPath, redFill);

    // Green line
    paint.color = AppColors.primary;
    final greenLine = Path();
    for (final p in [(0.0, 0.4), ...greenPoints]) {
      if (p.$1 == 0) greenLine.moveTo(0, size.height * p.$2);
      else greenLine.lineTo(size.width * p.$1, size.height * p.$2);
    }
    canvas.drawPath(greenLine, paint);

    // Red line
    paint.color = AppColors.moveBlunder;
    final redLine = Path();
    redLine.moveTo(size.width * 0.35, size.height * 0.4);
    for (final p in redPoints) {
      redLine.lineTo(size.width * p.$1, size.height * p.$2);
    }
    canvas.drawPath(redLine, paint);

    // Zero line
    final zeroPaint = Paint()
      ..color = AppColors.outlineVariant
      ..strokeWidth = 1;
    canvas.drawLine(
      Offset(0, size.height * 0.4),
      Offset(size.width, size.height * 0.4),
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

    // Endpoint dot
    final dotPaint = Paint()..color = AppColors.moveBlunder;
    canvas.drawCircle(
      Offset(size.width, size.height * 0.7),
      5,
      dotPaint,
    );
    canvas.drawCircle(
      Offset(size.width, size.height * 0.7),
      5,
      Paint()..color = Colors.white..style = PaintingStyle.stroke..strokeWidth = 1.5,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
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
              label: const Text('Otra partida'),
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.spaceMd),
                backgroundColor: AppColors.primary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}