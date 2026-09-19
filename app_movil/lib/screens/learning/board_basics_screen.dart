import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets.dart';

/// Pantalla 1: El Tablero - Fundamentos del tablero de ajedrez
class BoardBasicsScreen extends StatelessWidget {
  static const String routeName = '/learning/board-basics';

  const BoardBasicsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surface,
      body: Stack(
        children: [
          // Contenido scrollable
          CustomScrollView(
            slivers: [
              SliverPersistentHeader(
                pinned: true,
                delegate: _LearningHeaderDelegate(
                  category: 'FUNDAMENTOS',
                  title: 'El Tablero',
                  currentStep: 1,
                  totalSteps: 5,
                  onBack: null,
                  badgeText: '1 de 5',
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.margin),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Tarjeta principal con tablero interactivo
                      _buildMainBoardCard(),
                      const SizedBox(height: AppSpacing.spaceLg),

                      // 3 tarjetas informativas
                      _buildInfoCards(),
                      const SizedBox(height: AppSpacing.spaceLg),

                      // Callout importante
                      _buildImportantCallout(),
                      const SizedBox(height: AppSpacing.spaceLg),

                      // Comprobación rápida
                      _buildQuickCheck(),
                      const SizedBox(height: 100), // Espacio para bottom nav
                    ],
                  ),
                ),
              ),
            ],
          ),

          // Bottom Navigation
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: LearningBottomNav(
              onPrevious: null,
              onNext: () => context.go('/learning/pieces'),
              previousLabel: 'Anterior',
              nextLabel: 'Siguiente',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMainBoardCard() {
    return LearningCard(
      padding: AppSpacing.cardPaddingMd,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header de la tarjeta
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.spaceSm,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: AppColors.surfaceContainerLow,
                  borderRadius: AppRadius.radiusFull,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.school, size: 14, color: AppColors.secondary),
                    const SizedBox(width: 4),
                    Text(
                      'Fundamentos',
                      style: AppTextStyles.labelSm.copyWith(
                        color: AppColors.secondary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: AppColors.primary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Modo interactivo',
                    style: AppTextStyles.telemetrySm.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceXs),
          Text(
            '¿Cómo es el tablero de ajedrez?',
            style: AppTextStyles.headlineMd.copyWith(color: AppColors.onSurface),
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          Text(
            'El ajedrez se juega entre dos personas que mueven las piezas alternativamente. '
            'El juego se desarrolla sobre un tablero que contiene '
            '<strong>64 cuadrados</strong>, organizados en 8 filas y 8 columnas.',
            style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant),
          ),
          const SizedBox(height: AppSpacing.spaceLg),

          // Tablero interactivo
          InteractiveChessBoard(
            maxSize: 340,
            highlightedSquares: {
              'h1': Container(
                decoration: const BoxDecoration(
                  color: Colors.transparent,
                ),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Container(
                      width: 24,
                      height: 24,
                      decoration: BoxDecoration(
                        color: AppColors.secondaryFixed.withOpacity(0.5),
                        shape: BoxShape.circle,
                      ),
                    ),
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        color: AppColors.secondary,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.secondary.withOpacity(0.3),
                            blurRadius: 4,
                            spreadRadius: 1,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            },
            squareLabels: {'h1': 'h1'},
            onSquareTap: () {},
          ),
          const SizedBox(height: AppSpacing.spaceSm),

          // Etiqueta de la casilla h1
          Center(
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.spaceSm,
                vertical: 6,
              ),
              decoration: BoxDecoration(
                color: AppColors.surfaceContainer,
                borderRadius: AppRadius.radiusFull,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.verified,
                    size: 14,
                    color: AppColors.secondary,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Casilla ',
                    style: AppTextStyles.labelSm.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                  Text(
                    'h1',
                    style: AppTextStyles.labelSm.copyWith(
                      color: AppColors.secondary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    ': Blanca a la derecha',
                    style: AppTextStyles.labelSm.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoCards() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth > 600;

        if (isWide) {
          return Row(
            children: [
              Expanded(child: _buildInfoCard1()),
              const SizedBox(width: AppSpacing.spaceSm),
              Expanded(child: _buildInfoCard2()),
              const SizedBox(width: AppSpacing.spaceSm),
              Expanded(child: _buildInfoCard3()),
            ],
          );
        }

        return Column(
          children: [
            _buildInfoCard1(),
            const SizedBox(height: AppSpacing.spaceSm),
            _buildInfoCard2(),
            const SizedBox(height: AppSpacing.spaceSm),
            _buildInfoCard3(),
          ],
        );
      },
    );
  }

  Widget _buildInfoCard1() {
    return LearningInfoCard(
      icon: Icons.grid_view,
      title: '64 cuadrados',
      subtitle: '8 filas × 8 columnas',
      iconColor: AppColors.primary,
      iconBackgroundColor: AppColors.surfaceContainerLow,
      isColumnLayout: true,
    );
  }

  Widget _buildInfoCard2() {
    return LearningInfoCard(
      icon: Icons.palette,
      title: 'Colores',
      subtitle: 'Claros y oscuros alternados',
      iconColor: AppColors.secondary,
      iconBackgroundColor: AppColors.surfaceContainerLow,
      isColumnLayout: true,
    );
  }

  Widget _buildInfoCard3() {
    return LearningInfoCard(
      icon: Icons.explore,
      title: 'Orientación',
      subtitle: 'Cuadro blanco a la derecha',
      iconColor: AppColors.primary,
      iconBackgroundColor: AppColors.surfaceContainerLow,
      isColumnLayout: true,
    );
  }

  Widget _buildImportantCallout() {
    return InfoCallout(
      icon: Icons.check_circle,
      title: 'Importante',
      message:
          'El tablero debe estar orientado correctamente. Recuerda la regla de oro: '
          '<strong>cada jugador debe tener a su derecha un cuadro blanco</strong>.',
    );
  }

  Widget _buildQuickCheck() {
    return QuickCheck(
      title: 'Comprobación rápida',
      message:
          'Si eres Blancas, la casilla inferior derecha es ',
      richMessage: [
        TextSpan(
          text: 'Si eres Blancas, la casilla inferior derecha es ',
          style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
        ),
        TextSpan(
          text: 'h1',
          style: AppTextStyles.telemetrySm.copyWith(
            color: AppColors.primary,
            fontWeight: FontWeight.bold,
          ),
        ),
        TextSpan(
          text: '. Si eres Negras, es ',
          style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
        ),
        TextSpan(
          text: 'a8',
          style: AppTextStyles.telemetrySm.copyWith(
            color: AppColors.primary,
            fontWeight: FontWeight.bold,
          ),
        ),
        TextSpan(
          text: '. Ambas son siempre casillas claras.',
          style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
        ),
      ],
    );
  }
}

/// Delegate para el header persistente
class _LearningHeaderDelegate extends SliverPersistentHeaderDelegate {
  final String category;
  final String title;
  final int currentStep;
  final int totalSteps;
  final VoidCallback? onBack;
  final String? badgeText;

  _LearningHeaderDelegate({
    required this.category,
    required this.title,
    required this.currentStep,
    required this.totalSteps,
    this.onBack,
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
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.margin,
          AppSpacing.spaceSm,
          AppSpacing.margin,
          AppSpacing.spaceSm,
        ),
        decoration: BoxDecoration(
          color: AppColors.surfaceContainerLowest.withOpacity(0.95),
          border: Border(
            bottom: BorderSide(color: AppColors.outlineVariant, width: 1),
          ),
        ),
        child: Column(
          children: [
            Row(
              children: [
                if (onBack != null) ...[
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
                ],
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
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
            const SizedBox(height: AppSpacing.spaceXs),
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
  double get maxExtent => 100;

  @override
  double get minExtent => 100;

  @override
  bool shouldRebuild(covariant SliverPersistentHeaderDelegate oldDelegate) {
    return false;
  }
}