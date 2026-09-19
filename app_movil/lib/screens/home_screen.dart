import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../widgets.dart';
import '../services/auth_provider.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedTab = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _TopBar(),
            Expanded(
              child: IndexedStack(
                index: _selectedTab,
                children: [
                  _HomeTab(),
                  _StatsTab(),
                  _ProgressTab(),
                  _ProfileTab(),
                ],
              ),
            ),
            _BottomNavBar(
              currentIndex: _selectedTab,
              onTap: (index) => setState(() => _selectedTab = index),
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
    final user = context.watch<AuthProvider>().user;
    final nombre = user?.nombre ?? 'Jugador';
    final nivel = user?.nivelEstimado ?? 1;
    final rango = user?.rangoEstimado ?? 'Principiante';
    final rangoColor = _getRangoColor(rango);

    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Row(
        children: [
          CircleAvatar(
            radius: 24,
            backgroundColor: AppColors.secondary.withOpacity(0.15),
            child: Icon(Icons.person, color: AppColors.secondary, size: 26),
          ),
          const SizedBox(width: AppSpacing.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Hola, ${nombre.split(' ').first}',
                  style: AppTextStyles.headlineSm.copyWith(
                    color: AppColors.onSurface,
                  ),
                ),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.spaceSm,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: rangoColor.withOpacity(0.15),
                        borderRadius: AppRadius.radiusFull,
                      ),
                      child: Text(
                        '$rango • Nivel $nivel',
                        style: AppTextStyles.labelSm.copyWith(
                          color: rangoColor,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          GlassCard(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.spaceSm, // Reducido para evitar recortes
              vertical: AppSpacing.spaceSm,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.local_fire_department, color: AppColors.tertiary, size: 20),
                const SizedBox(width: AppSpacing.spaceXs),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'Racha',
                      style: AppTextStyles.labelSm.copyWith(
                        color: AppColors.onSurfaceVariant,
                        fontSize: 9,
                      ),
                    ),
                    Text(
                      '3 días',
                      style: AppTextStyles.labelMd.copyWith(
                        color: AppColors.onSurface,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Color _getRangoColor(String rango) {
    switch (rango) {
      case 'Principiante':
        return AppColors.primary;
      case 'Intermedio':
        return AppColors.secondary;
      case 'Avanzado':
        return AppColors.tertiary;
      default:
        return AppColors.primary;
    }
  }
}

class _HomeTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _HeroBanner(),
          const SizedBox(height: AppSpacing.spaceXl),
          _StatsRow(),
          const SizedBox(height: AppSpacing.spaceXl),
          _SkillsProgressCard(),
          const SizedBox(height: AppSpacing.spaceXl),
          _QuickActions(),
        ],
      ),
    );
  }
}

class _HeroBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 180),
      decoration: BoxDecoration(
        borderRadius: AppRadius.radiusXl,
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF033B2A),
            Color(0xFF05573E),
            Color(0xFF07704F),
          ],
        ),
        boxShadow: AppShadows.level2,
      ),
      child: Stack(
        children: [
          Positioned(
            right: -20,
            top: -40,
            child: Opacity(
              opacity: 0.15,
              child: Transform.rotate(
                angle: 0.3,
                child: const Text('♔', style: TextStyle(fontSize: 200)),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.spaceXl),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'Es tu turno de jugar',
                  style: AppTextStyles.headlineLg.copyWith(color: AppColors.onPrimary),
                ),
                const SizedBox(height: AppSpacing.spaceSm),
                Text(
                  'Enfréntate a la IA y sigue mejorando tu nivel de ajedrez.',
                  style: AppTextStyles.bodySm.copyWith(
                    color: AppColors.primaryContainer,
                  ),
                ),
                const SizedBox(height: AppSpacing.spaceMd),
                FilledButton.icon(
                  onPressed: () => context.go('/config'),
                  icon: const Icon(Icons.play_arrow, size: 20),
                  label: const Text('Jugar'),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.onPrimary,
                    foregroundColor: AppColors.primary,
                  ),
                ),
              ],
            ),
          ),
          // Se eliminó la caja amarilla con la frase motivacional a petición del usuario.
        ],
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Row(
        children: [
          _StatItem(
            icon: Icons.casino_outlined,
            color: AppColors.primary,
            label: 'Partidas jugadas',
            value: '12',
          ),
          _StatDivider(),
          _StatItem(
            icon: Icons.emoji_events_outlined,
            color: AppColors.primary,
            label: 'Victorias',
            value: '4',
          ),
          _StatDivider(),
          _StatItem(
            icon: Icons.psychology_outlined,
            color: AppColors.secondary,
            label: 'Precisión promedio',
            value: '68%',
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  final String value;

  const _StatItem({
    required this.icon,
    required this.color,
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
              color: color.withOpacity(0.15),
              borderRadius: AppRadius.radiusMd,
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          Text(
            label,
            style: AppTextStyles.labelSm.copyWith(
              color: AppColors.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: AppTextStyles.headlineMd.copyWith(
              color: AppColors.onSurface,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _StatDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      width: 1,
      color: AppColors.outlineVariant,
    );
  }
}

class _SkillsProgressCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Mapa de habilidades',
            style: AppTextStyles.headlineSm.copyWith(color: AppColors.onSurface),
          ),
          const SizedBox(height: AppSpacing.spaceLg),
          _RadarChartPlaceholder(),
          const SizedBox(height: AppSpacing.spaceLg),
          _SkillBars(),
        ],
      ),
    );
  }
}

class _RadarChartPlaceholder extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: CustomPaint(
        painter: _RadarChartPainter(),
        child: Center(
          child: Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.surfaceContainerLowest,
              boxShadow: AppShadows.level1,
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.radar, color: AppColors.primary, size: 32),
                const SizedBox(height: 4),
                Text(
                  '68%',
                  style: AppTextStyles.telemetryLg.copyWith(color: AppColors.primary),
                ),
                Text(
                  'Global',
                  style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RadarChartPainter extends CustomPainter {
  final List<double> values = [0.68, 0.45, 0.72, 0.38, 0.55, 0.62];
  final List<String> labels = ['Aperturas', 'Táctica', 'Finales', 'Posicional', 'Cálculo', 'Tiempo'];

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 20;
    final sides = 6;
    final angleStep = 2 * 3.14159 / sides;

    // Concentric polygons
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = AppColors.outlineVariant;

    for (int i = 1; i <= 4; i++) {
      final r = radius * i / 4;
      final path = Path();
      for (int j = 0; j < sides; j++) {
        final angle = j * angleStep - 3.14159 / 2;
        final x = center.dx + r * angle.cos();
        final y = center.dy + r * angle.sin();
        if (j == 0) path.moveTo(x, y);
        else path.lineTo(x, y);
      }
      path.close();
      canvas.drawPath(path, paint);
    }

    // Axes
    for (int j = 0; j < sides; j++) {
      final angle = j * angleStep - 3.14159 / 2;
      final x = center.dx + radius * angle.cos();
      final y = center.dy + radius * angle.sin();
      canvas.drawLine(center, Offset(x, y), paint);
    }

    // Data polygon
    final dataPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = AppColors.primary.withOpacity(0.15);
    final dataStrokePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..color = AppColors.primary;

    final dataPath = Path();
    for (int j = 0; j < sides; j++) {
      final angle = j * angleStep - 3.14159 / 2;
      final r = radius * values[j];
      final x = center.dx + r * angle.cos();
      final y = center.dy + r * angle.sin();
      if (j == 0) dataPath.moveTo(x, y);
      else dataPath.lineTo(x, y);
    }
    dataPath.close();
    canvas.drawPath(dataPath, dataPaint);
    canvas.drawPath(dataPath, dataStrokePaint);

    // Labels
    final textPainter = TextPainter(textDirection: TextDirection.ltr);
    for (int j = 0; j < sides; j++) {
      final angle = j * angleStep - 3.14159 / 2;
      final r = radius + 24;
      final x = center.dx + r * angle.cos();
      final y = center.dy + r * angle.sin();
      textPainter.text = TextSpan(
        text: labels[j],
        style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant),
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(x - textPainter.width / 2, y - textPainter.height / 2));
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

extension _Trig on double {
  double cos() => math.cos(this);
  double sin() => math.sin(this);
}

class _SkillBars extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final skills = [
      ('Aperturas', 0.68, AppColors.primary),
      ('Táctica', 0.45, AppColors.secondary),
      ('Finales', 0.72, AppColors.primary),
      ('Posicional', 0.38, AppColors.tertiary),
      ('Cálculo', 0.55, AppColors.secondary),
      ('Gestión tiempo', 0.62, AppColors.primary),
    ];

    return Column(
      children: skills.map((skill) => Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.spaceMd),
        child: _SkillBar(
          name: skill.$1,
          progress: skill.$2,
          color: skill.$3,
        ),
      )).toList(),
    );
  }
}

class _SkillBar extends StatelessWidget {
  final String name;
  final double progress;
  final Color color;

  const _SkillBar({
    required this.name,
    required this.progress,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(name, style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurface)),
            Text('${(progress * 100).round()}%', style: AppTextStyles.telemetrySm.copyWith(color: color)),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: AppRadius.radiusFull,
          child: LinearProgressIndicator(
            value: progress,
            minHeight: 6,
            backgroundColor: AppColors.surfaceVariant,
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        ),
      ],
    );
  }
}

class _QuickActions extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Acciones rápidas',
          style: AppTextStyles.headlineSm.copyWith(color: AppColors.onSurface),
        ),
        const SizedBox(height: AppSpacing.spaceMd),
        Row(
          children: [
            Expanded(
              child: _ActionCard(
                icon: Icons.play_arrow,
                title: 'Jugar',
                subtitle: 'Nueva partida',
                color: AppColors.primary,
                onTap: () => context.go('/config'),
              ),
            ),
            const SizedBox(width: AppSpacing.spaceMd),
            Expanded(
              child: _ActionCard(
                icon: Icons.school_outlined,
                title: 'Aprender',
                subtitle: 'Lecciones y puzzles',
                color: AppColors.secondary,
                onTap: () => context.go('/learning/board-basics'),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.spaceMd),
        Row(
          children: [
            Expanded(
              child: _ActionCard(
                icon: Icons.bar_chart_outlined,
                title: 'Progreso',
                subtitle: 'Estadísticas',
                color: AppColors.tertiary,
                onTap: () {},
              ),
            ),
            const SizedBox(width: AppSpacing.spaceMd),
            Expanded(
              child: _ActionCard(
                icon: Icons.settings_outlined,
                title: 'Configuración',
                subtitle: 'Preferencias',
                color: AppColors.onSurfaceVariant,
                onTap: () {},
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: AppRadius.radiusLg,
      child: TacticalCard(
        padding: const EdgeInsets.all(AppSpacing.spaceLg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(AppSpacing.spaceSm),
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                borderRadius: AppRadius.radiusMd,
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            const SizedBox(height: AppSpacing.spaceMd),
            Text(
              title,
              style: AppTextStyles.bodyLg.copyWith(color: AppColors.onSurface),
            ),
            Text(
              subtitle,
              style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatsTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const Center(child: Text('Estadísticas - Próximamente'));
  }
}

class _ProgressTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const Center(child: Text('Progreso - Próximamente'));
  }
}

class _ProfileTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          GlassCard(
            padding: const EdgeInsets.all(AppSpacing.spaceLg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(user?.nombre ?? 'Jugador', style: AppTextStyles.headlineSm.copyWith(color: AppColors.onSurface)),
                const SizedBox(height: AppSpacing.spaceXs),
                Text(user?.email ?? '', style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant)),
                const SizedBox(height: AppSpacing.spaceXs),
                Text('Rol: ${user?.rol ?? '-'}', style: AppTextStyles.bodySm.copyWith(color: AppColors.primary)),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.spaceLg),
          OutlinedButton.icon(
            onPressed: () async {
              await auth.logout();
              if (context.mounted) context.go('/login');
            },
            icon: const Icon(Icons.logout),
            label: const Text('Cerrar sesión'),
          ),
        ],
      ),
    );
  }
}

class _BottomNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  const _BottomNavBar({
    required this.currentIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerLowest,
        border: Border(top: BorderSide(color: AppColors.outlineVariant)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            _NavItem(
              index: 0,
              icon: Icons.home_outlined,
              activeIcon: Icons.home,
              label: 'Inicio',
              isActive: currentIndex == 0,
              onTap: () => onTap(0),
            ),
            _NavItem(
              index: 1,
              icon: Icons.bar_chart_outlined,
              activeIcon: Icons.bar_chart,
              label: 'Stats',
              isActive: currentIndex == 1,
              onTap: () => onTap(1),
            ),
            _NavItem(
              index: 2,
              icon: Icons.trending_up_outlined,
              activeIcon: Icons.trending_up,
              label: 'Progreso',
              isActive: currentIndex == 2,
              onTap: () => onTap(2),
            ),
            _NavItem(
              index: 3,
              icon: Icons.person_outline,
              activeIcon: Icons.person,
              label: 'Perfil',
              isActive: currentIndex == 3,
              onTap: () => onTap(3),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final int index;
  final IconData icon;
  final IconData activeIcon;
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _NavItem({
    required this.index,
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.spaceSm),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isActive ? activeIcon : icon,
                color: isActive ? AppColors.primary : AppColors.onSurfaceVariant,
                size: 24,
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: AppTextStyles.labelSm.copyWith(
                  color: isActive ? AppColors.primary : AppColors.onSurfaceVariant,
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}