import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../widgets.dart';

class EvaluationResultScreen extends StatelessWidget {
  final int level;
  final String rank; // 'Principiante', 'Intermedio', 'Avanzado'
  final double accuracy;
  final int gamesPlayed;

  const EvaluationResultScreen({
    super.key,
    required this.level,
    required this.rank,
    required this.accuracy,
    required this.gamesPlayed,
  });

  @override
  Widget build(BuildContext context) {
    final rankColor = _getRankColor(rank);
    final rankIcon = _getRankIcon(rank);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Stack(
          children: [
            Column(
              children: [
                _TopBar(),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(AppSpacing.margin),
                    child: Column(
                      children: [
                        _TrophySection(
                          rank: rank,
                          rankColor: rankColor,
                          rankIcon: rankIcon,
                        ),
                        const SizedBox(height: AppSpacing.spaceXl),
                        _ResultText(rank: rank),
                        const SizedBox(height: AppSpacing.spaceLg),
                        _PotentialBox(),
                        const SizedBox(height: AppSpacing.spaceXl),
                        _MetricsRow(
                          level: level,
                          accuracy: accuracy,
                          gamesPlayed: gamesPlayed,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.margin),
                child: FilledButton(
                  onPressed: () => context.go('/home'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: AppSpacing.spaceLg),
                    backgroundColor: rankColor,
                  ),
                  child: const Text('Comenzar a jugar'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getRankColor(String rank) {
    switch (rank) {
      case 'Principiante': return AppColors.primary;
      case 'Intermedio': return AppColors.secondary;
      case 'Avanzado': return AppColors.tertiary;
      default: return AppColors.primary;
    }
  }

  IconData _getRankIcon(String rank) {
    switch (rank) {
      case 'Principiante': return Icons.emoji_events_outlined;
      case 'Intermedio': return Icons.star_outline;
      case 'Avanzado': return Icons.diamond_outlined;
      default: return Icons.emoji_events_outlined;
    }
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
            onPressed: () => context.go('/mode-selection'),
            icon: const Icon(Icons.chevron_left, color: AppColors.onSurface),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Resultado de tu evaluación',
                  style: AppTextStyles.headlineSm.copyWith(
                    color: AppColors.onSurface,
                  ),
                ),
                Text(
                  'Gracias por completar la prueba',
                  style: AppTextStyles.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          _BrandLogoSmall(),
        ],
      ),
    );
  }
}

class _BrandLogoSmall extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: AppRadius.radiusMd,
          ),
          child: const Icon(Icons.casino, color: AppColors.onPrimary, size: 18),
        ),
        const SizedBox(width: AppSpacing.spaceXs),
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              'ChessIA',
              style: AppTextStyles.labelMd.copyWith(
                color: AppColors.onSurface,
                fontWeight: FontWeight.w800,
              ),
            ),
            Text(
              'Aprende. Juega. Mejora.',
              style: AppTextStyles.labelSm.copyWith(
                color: AppColors.onSurfaceVariant,
                fontSize: 7,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _TrophySection extends StatelessWidget {
  final String rank;
  final Color rankColor;
  final IconData rankIcon;

  const _TrophySection({
    required this.rank,
    required this.rankColor,
    required this.rankIcon,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceXl),
      child: Column(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [rankColor.withOpacity(0.1), rankColor.withOpacity(0.05)],
                  ),
                ),
              ),
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      rankColor.withOpacity(0.3),
                      rankColor,
                    ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: rankColor.withOpacity(0.4),
                      blurRadius: 20,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: Icon(rankIcon, color: AppColors.onPrimary, size: 40),
              ),
              Positioned(
                bottom: -12,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.spaceLg,
                    vertical: AppSpacing.spaceSm,
                  ),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [rankColor, rankColor.withOpacity(0.8)],
                    ),
                    borderRadius: AppRadius.radiusFull,
                    boxShadow: [
                      BoxShadow(
                        color: rankColor.withOpacity(0.4),
                        blurRadius: 8,
                        spreadRadius: 0,
                      ),
                    ],
                  ),
                  child: Text(
                    rank,
                    style: AppTextStyles.labelMd.copyWith(
                      color: AppColors.onPrimary,
                      fontSize: 16,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceXl),
        ],
      ),
    );
  }
}

class _ResultText extends StatelessWidget {
  final String rank;

  const _ResultText({required this.rank});

  @override
  Widget build(BuildContext context) {
    String message;
    String detail;

    switch (rank) {
      case 'Principiante':
        message = '¡Muy bien!';
        detail = 'Estás dando tus primeros pasos en el ajedrez. Has demostrado conocimientos básicos del juego. Con práctica y constancia podrás avanzar al siguiente nivel.';
        break;
      case 'Intermedio':
        message = '¡Excelente!';
        detail = 'Tienes un buen entendimiento del ajedrez. Conoces aperturas, tácticas básicas y finales elementales. Sigue así para alcanzar nivel avanzado.';
        break;
      case 'Avanzado':
        message = '¡Impresionante!';
        detail = 'Demuestras un nivel sólido con buena comprensión posicional y táctica. Estás listo para competir en torneos y seguir perfeccionando tu juego.';
        break;
      default:
        message = '¡Bien hecho!';
        detail = 'Has completado la evaluación inicial.';
    }

    return Column(
      children: [
        Text(
          message,
          style: AppTextStyles.displayLgMobile.copyWith(
            color: AppColors.onSurface,
          ),
        ),
        const SizedBox(height: AppSpacing.spaceMd),
        Text(
          detail,
          style: AppTextStyles.bodyMd.copyWith(
            color: AppColors.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _PotentialBox extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Row(
        children: [
          Column(
            children: [
              _BarSegment(height: 0.35),
              _BarSegment(height: 0.65),
              _BarSegment(height: 1.0),
            ],
          ),
          const SizedBox(width: AppSpacing.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Tienes un gran potencial.',
                  style: AppTextStyles.headlineSm.copyWith(
                    color: AppColors.primary,
                  ),
                ),
                const SizedBox(height: AppSpacing.spaceXs),
                Text(
                  'Sigue jugando, aprendiendo y desafiándote para mejorar tu nivel.',
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

class _BarSegment extends StatelessWidget {
  final double height;

  const _BarSegment({required this.height});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 2),
        child: FractionallySizedBox(
          heightFactor: height,
          alignment: Alignment.bottomCenter,
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: AppRadius.radiusSm,
            ),
          ),
        ),
      ),
    );
  }
}

class _MetricsRow extends StatelessWidget {
  final int level;
  final double accuracy;
  final int gamesPlayed;

  const _MetricsRow({
    required this.level,
    required this.accuracy,
    required this.gamesPlayed,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Row(
        children: [
          _MetricItem(
            icon: Icons.casino_outlined,
            iconColor: AppColors.primary,
            label: 'Nivel asignado',
            value: '$level',
          ),
          _MetricDivider(),
          _MetricItem(
            icon: Icons.bar_chart,
            iconColor: AppColors.secondary,
            label: 'Precisión',
            value: '${accuracy.round()}%',
          ),
          _MetricDivider(),
          _MetricItem(
            icon: Icons.psychology_outlined,
            iconColor: AppColors.tertiary,
            label: 'Partidas test',
            value: '$gamesPlayed',
          ),
        ],
      ),
    );
  }
}

class _MetricItem extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;

  const _MetricItem({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
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
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: AppTextStyles.headlineMd.copyWith(color: AppColors.onSurface),
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
      height: 48,
      width: 1,
      color: AppColors.outlineVariant,
    );
  }
}