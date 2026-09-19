import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets.dart';

/// Pantalla 4: La Posición Inicial - Posición completa de las piezas
class InitialPositionScreen extends StatelessWidget {
  static const String routeName = '/learning/initial-position';

  const InitialPositionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surface,
      body: Stack(
        children: [
          SafeArea(
            bottom: false,
            child: CustomScrollView(
            slivers: [
              SliverPersistentHeader(
                pinned: true,
                delegate: _InitialPositionHeaderDelegate(
                  category: 'APRENDIENDO AJEDREZ',
                  title: 'La Posición Inicial',
                  currentStep: 4,
                  totalSteps: 5,
                  onBack: () => context.go('/learning-path'),
                  badgeText: '4 de 5',
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.margin),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildIntroCard(),
                      const SizedBox(height: AppSpacing.spaceLg),
                      _buildMainBoard(),
                      const SizedBox(height: AppSpacing.spaceLg),
                      _buildGoldenRules(),
                      const SizedBox(height: AppSpacing.spaceLg),
                      _buildMoveVsCapture(),
                      const SizedBox(height: AppSpacing.spaceLg),
                      _buildFinalAdvice(),
                      const SizedBox(height: 100),
                    ],
                  ),
                ),
              ),
            ],
            ),
          ),

          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: LearningBottomNav(
              onPrevious: () => context.go('/learning/ranks-files'),
              onNext: null,
              previousLabel: 'Anterior',
              nextLabel: 'Fin',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildIntroCard() {
    return LearningCard(
      padding: AppSpacing.cardPaddingMd,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.spaceSm,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFFECFDF5),
                    borderRadius: AppRadius.radiusFull,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.school, size: 14, color: Color(0xFF087F5B)),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          'FUNDAMENTOS',
                          style: AppTextStyles.labelSm.copyWith(
                            color: Color(0xFF087F5B),
                            fontWeight: FontWeight.bold,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.spaceSm),
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.spaceSm,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainerLow,
                    borderRadius: AppRadius.radiusFull,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: AppColors.primary,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Flexible(
                        child: Text(
                          'Posición completa',
                          style: AppTextStyles.telemetrySm.copyWith(
                            color: AppColors.onSurfaceVariant,
                            fontWeight: FontWeight.bold,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          Text(
            '¿Cómo se colocan las piezas al inicio?',
            style: AppTextStyles.headlineMd.copyWith(color: AppColors.onSurface),
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          MarkupText(
            'El tablero se mira desde el lado de las blancas. Cada bando comienza con '
            '<strong>16 piezas</strong> preparadas simétricamente para la partida.',
            style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant),
          ),
        ],
      ),
    );
  }

  Widget _buildMainBoard() {
    return LearningCard(
      padding: AppSpacing.cardPaddingSm,
      child: Column(
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              return Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _StatusItem(
                    icon: Icons.circle,
                    iconColor: const Color(0xFF0F172A),
                    label: 'Negras (Filas 7-8)',
                  ),
                  _StatusItem(
                    icon: Icons.casino,
                    iconColor: AppColors.onSurfaceVariant,
                    label: '32 Piezas',
                    showChip: true,
                  ),
                  _StatusItem(
                    icon: Icons.circle,
                    iconColor: AppColors.surfaceContainerLowest,
                    label: 'Blancas (Filas 1-2)',
                    iconBorder: Border.all(color: AppColors.primary, width: 2),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          _buildFullBoard(),
          const SizedBox(height: AppSpacing.spaceMd),
          Row(
            children: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
                .map(
                  (letter) => Expanded(
                    child: Center(
                      child: Text(
                        letter,
                        style: AppTextStyles.telemetrySm.copyWith(
                          color: AppColors.outline,
                          fontWeight: FontWeight.bold,
                          fontSize: 10,
                        ),
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.spaceMd,
              vertical: AppSpacing.spaceSm,
            ),
            decoration: BoxDecoration(
              color: AppColors.surfaceContainerLow,
              borderRadius: AppRadius.radiusFull,
              border: Border.all(color: AppColors.outlineVariant),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
            child: Wrap(
              alignment: WrapAlignment.center,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  'd1 = Dama Blanca ',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
                Text(
                  '(casilla clara)',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  ' • ',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.outline,
                  ),
                ),
                Text(
                  'd8 = Dama Negra ',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
                Text(
                  '(casilla oscura)',
                  style: AppTextStyles.labelSm.copyWith(
                    color: const Color(0xFF0284C7),
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ), // Cierra SingleChildScrollView
        ),
      ],
      ),
    );
  }

  Widget _buildFullBoard() {
    final boardData = [
      [
        {'piece': '♜', 'color': 'black', 'bg': 'white'},
        {'piece': '♞', 'color': 'black', 'bg': 'dark'},
        {'piece': '♝', 'color': 'black', 'bg': 'white'},
        {'piece': '♛', 'color': 'black', 'bg': 'dark', 'highlight': true},
        {'piece': '♚', 'color': 'black', 'bg': 'white'},
        {'piece': '♝', 'color': 'black', 'bg': 'dark'},
        {'piece': '♞', 'color': 'black', 'bg': 'white'},
        {'piece': '♜', 'color': 'black', 'bg': 'dark'},
      ],
      [
        {'piece': '♟', 'color': 'black', 'bg': 'dark'},
        {'piece': '♟', 'color': 'black', 'bg': 'white'},
        {'piece': '♟', 'color': 'black', 'bg': 'dark'},
        {'piece': '♟', 'color': 'black', 'bg': 'white'},
        {'piece': '♟', 'color': 'black', 'bg': 'dark'},
        {'piece': '♟', 'color': 'black', 'bg': 'white'},
        {'piece': '♟', 'color': 'black', 'bg': 'dark'},
        {'piece': '♟', 'color': 'black', 'bg': 'white'},
      ],
      List.generate(8, (i) => {'empty': true, 'bg': i % 2 == 0 ? 'white' : 'dark'}),
      List.generate(8, (i) => {'empty': true, 'bg': i % 2 == 1 ? 'white' : 'dark'}),
      List.generate(8, (i) => {'empty': true, 'bg': i % 2 == 0 ? 'white' : 'dark'}),
      List.generate(8, (i) => {'empty': true, 'bg': i % 2 == 1 ? 'white' : 'dark'}),
      [
        {'piece': '♙', 'color': 'white', 'bg': 'white'},
        {'piece': '♙', 'color': 'white', 'bg': 'dark'},
        {'piece': '♙', 'color': 'white', 'bg': 'white'},
        {'piece': '♙', 'color': 'white', 'bg': 'dark'},
        {'piece': '♙', 'color': 'white', 'bg': 'white'},
        {'piece': '♙', 'color': 'white', 'bg': 'dark'},
        {'piece': '♙', 'color': 'white', 'bg': 'white'},
        {'piece': '♙', 'color': 'white', 'bg': 'dark'},
      ],
      [
        {'piece': '♖', 'color': 'white', 'bg': 'dark'},
        {'piece': '♘', 'color': 'white', 'bg': 'white'},
        {'piece': '♗', 'color': 'white', 'bg': 'dark'},
        {'piece': '♕', 'color': 'white', 'bg': 'white', 'highlight': true},
        {'piece': '♔', 'color': 'white', 'bg': 'dark'},
        {'piece': '♗', 'color': 'white', 'bg': 'white'},
        {'piece': '♘', 'color': 'white', 'bg': 'dark'},
        {'piece': '♖', 'color': 'white', 'bg': 'white'},
      ],
    ];

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: AppRadius.radiusXl,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: List.generate(8, (rowIndex) {
          final row = boardData[rowIndex];
          final rankNumber = 8 - rowIndex;
          return _buildBoardRow(row: row, rankNumber: rankNumber);
        }),
      ),
    );
  }

  Widget _buildBoardRow({
    required List<Map<String, dynamic>> row,
    required int rankNumber,
  }) {
    return Container(
      height: 36,
      child: Row(
        children: [
          Container(
            width: 20,
            alignment: Alignment.centerLeft,
            padding: const EdgeInsets.only(left: 4),
            child: Text(
              '$rankNumber',
              style: AppTextStyles.telemetrySm.copyWith(
                color: rankNumber % 2 == 0
                    ? AppColors.outlineVariant
                    : AppColors.outline,
                fontWeight: FontWeight.bold,
                fontSize: 9,
              ),
            ),
          ),
          Expanded(
            child: Row(
              children: List.generate(8, (colIndex) {
                final cell = row[colIndex];
                final isLight = cell['bg'] == 'white';

                if (cell['empty'] == true) {
                  return Expanded(
                    child: Container(
                      color: isLight ? Colors.white : const Color(0xFFB4C6D4),
                    ),
                  );
                }

                final piece = cell['piece'] as String;
                final color = cell['color'] as String;
                final highlight = cell['highlight'] == true;

                return Expanded(
                  child: Container(
                    color: isLight ? Colors.white : const Color(0xFFB4C6D4),
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        Text(
                          piece,
                          style: TextStyle(
                            fontSize: 24,
                            color: color == 'white'
                                ? const Color(0xFF059669)
                                : const Color(0xFF0F172A),
                            fontWeight: FontWeight.bold,
                            shadows: [
                              Shadow(
                                color: color == 'white'
                                    ? const Color(0xFF059669).withValues(alpha: 0.35)
                                    : Colors.black.withValues(alpha: 0.45),
                                blurRadius: 2,
                                offset: const Offset(0, 1),
                              ),
                            ],
                          ),
                        ),
                        if (highlight)
                          Positioned(
                            bottom: 3,
                            child: Container(
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                color: color == 'white'
                                    ? const Color(0xFF059669)
                                    : const Color(0xFF0284C7),
                                shape: BoxShape.circle,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              }),
            ),
          ),
          Container(
            width: 20,
            alignment: Alignment.centerRight,
            padding: const EdgeInsets.only(right: 4),
            child: Text(
              '$rankNumber',
              style: AppTextStyles.telemetrySm.copyWith(
                color: rankNumber % 2 == 0
                    ? AppColors.outlineVariant
                    : AppColors.outline,
                fontWeight: FontWeight.bold,
                fontSize: 9,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGoldenRules() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: AppSpacing.spaceXs),
          child: Text(
            'Reglas de oro de colocación',
            style: AppTextStyles.headlineSm.copyWith(
              color: AppColors.onSurface,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.spaceSm),
        GoldenRuleCallout(
          icon: Icons.emoji_events,
          title: 'La Dama y el Rey',
          message:
              'La Dama siempre va en la casilla de su <strong>propio color</strong>: '
              'la dama blanca en casilla clara (<strong>d1</strong>) '
              'y la dama negra en casilla oscura (<strong>d8</strong>). '
              'El Rey se sitúa justo a su lado en la columna <strong>e</strong>.',
          iconColor: const Color(0xFF0284C7),
          iconBackgroundColor: const Color(0xFFE0F2FE),
        ),
        const SizedBox(height: AppSpacing.spaceSm),
        GoldenRuleCallout(
          icon: Icons.compare_arrows,
          title: 'Enfrentados simétricamente',
          message:
              'Los Reyes y las Damas rivales se miran de frente a lo largo de las columnas '
              'centrales <strong>d</strong> y '
              '<strong>e</strong>, '
              'garantizando perfecta simetría en el despliegue.',
          iconColor: AppColors.primary,
          iconBackgroundColor: AppColors.primaryContainer,
        ),
        const SizedBox(height: AppSpacing.spaceSm),
        GoldenRuleCallout(
          icon: Icons.flag,
          title: 'Las blancas comienzan',
          message:
              'El jugador con piezas blancas siempre realiza el primer movimiento de la partida '
              'por convención y reglamento oficial internacional.',
          iconColor: const Color(0xFF2563EB),
          iconBackgroundColor: const Color(0xFFEFF6FF),
        ),
      ],
    );
  }

  Widget _buildMoveVsCapture() {
    return MoveVsCaptureSection();
  }

  Widget _buildFinalAdvice() {
    return FinalAdviceCallout(
      title: 'Consejo',
      message:
          'Al inicio, todas las piezas están ordenadas y listas para su desarrollo. '
          'Esta posición inicial es universal y nunca varía en ajedrez estándar.',
    );
  }
}

class _StatusItem extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String label;
  final bool showChip;
  final Border? iconBorder;

  const _StatusItem({
    required this.icon,
    required this.iconColor,
    required this.label,
    this.showChip = false,
    this.iconBorder,
  });

  @override
  Widget build(BuildContext context) {
    return Flexible(
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: iconColor,
              shape: BoxShape.circle,
              border: iconBorder,
            ),
          ),
          const SizedBox(width: 6),
          if (showChip)
            Flexible(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: AppColors.surfaceContainerLow,
                  borderRadius: AppRadius.radiusFull,
                ),
                child: Text(
                  label,
                  style: AppTextStyles.telemetrySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                    fontWeight: FontWeight.bold,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            )
          else
            Flexible(
              child: Text(
                label,
                style: AppTextStyles.bodySm.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
        ],
      ),
    );
  }
}

class _InitialPositionHeaderDelegate extends SliverPersistentHeaderDelegate {
  final String category;
  final String title;
  final int currentStep;
  final int totalSteps;
  final VoidCallback onBack;
  final String? badgeText;

  _InitialPositionHeaderDelegate({
    required this.category,
    required this.title,
    required this.currentStep,
    required this.totalSteps,
    required this.onBack,
    this.badgeText,
  });

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    final progress = currentStep / totalSteps;
    final opacity = (1 - shrinkOffset / 80).clamp(0.0, 1.0);

    return Opacity(
      opacity: opacity,
      child: Container(
        height: 88,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.margin),
        decoration: BoxDecoration(
          color: AppColors.surfaceContainerLowest.withOpacity(0.95),
          border: Border(
            bottom: BorderSide(color: AppColors.outlineVariant, width: 1),
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(
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
                const SizedBox(width: AppSpacing.spaceSm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        category,
                        style: AppTextStyles.labelSm.copyWith(
                          color: AppColors.primary,
                          letterSpacing: 1.0,
                        ),
                      ),
                      Text(
                        title,
                        style: AppTextStyles.headlineSm.copyWith(
                          color: AppColors.onSurface,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                if (badgeText != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.spaceSm,
                      vertical: AppSpacing.spaceXs,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.1),
                      borderRadius: AppRadius.radiusFull,
                      border: Border.all(
                        color: AppColors.primary.withOpacity(0.3),
                      ),
                    ),
                    child: Text(
                      badgeText!,
                      style: AppTextStyles.telemetrySm.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            LinearProgressIndicator(
              value: progress,
              backgroundColor: AppColors.surfaceContainerHighest,
              valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
              minHeight: 4,
              borderRadius: AppRadius.radiusFull,
            ),
          ],
        ),
      ),
    );
  }

  @override
  double get maxExtent => 88;

  @override
  double get minExtent => 88;

  @override
  bool shouldRebuild(covariant SliverPersistentHeaderDelegate oldDelegate) {
    return false;
  }
}

