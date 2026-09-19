import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets.dart';

/// Pantalla 3: Filas y Columnas - Coordenadas del tablero
class RanksFilesScreen extends StatelessWidget {
  static const String routeName = '/learning/ranks-files';

  const RanksFilesScreen({super.key});

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
                delegate: _RanksFilesHeaderDelegate(
                  category: 'APRENDIENDO AJEDREZ',
                  title: 'Filas y Columnas',
                  currentStep: 3,
                  totalSteps: 5,
                  onBack: () => context.go('/learning/pieces'),
                  badgeText: '3 de 5',
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.margin),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Tarjeta principal con tablero y coordenadas
                      _buildMainBoardCard(),
                      const SizedBox(height: AppSpacing.spaceLg),

                      // 3 tarjetas explicativas
                      _buildInfoCards(),
                      const SizedBox(height: AppSpacing.spaceLg),

                      // Callout regla de nombrado
                      _buildNamingRuleCallout(),
                      const SizedBox(height: AppSpacing.spaceLg),

                      // Comprobación rápida
                      _buildQuickCheck(),
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
              onPrevious: () => context.go('/learning/pieces'),
              onNext: () => context.go('/learning/initial-position'),
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
              Flexible(
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
                    const SizedBox(width: 4),
                    Flexible(
                      child: Text(
                        'Modo interactivo',
                        style: AppTextStyles.telemetrySm.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w600,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceXs),
          Text(
            '¿Qué son las filas y las columnas?',
            style: AppTextStyles.headlineMd.copyWith(color: AppColors.onSurface),
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          MarkupText(
            'Para nombrar cada casilla y mover las piezas, el tablero se divide en '
            'líneas horizontales llamadas <strong>filas</strong> '
            '(numeradas del 1 al 8) y líneas verticales llamadas '
            '<strong>columnas</strong> '
            '(identificadas con letras de la \'a\' a la \'h\').',
            style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant),
          ),
          const SizedBox(height: AppSpacing.spaceLg),

          InteractiveChessBoard(
            maxSize: 340,
            highlightedSquares: {
              // Columna e (vertical)
              'e8': _buildHighlightedSquare(AppColors.secondaryFixed.withOpacity(0.5), text: 'e8', textColor: AppColors.onSecondaryFixedVariant),
              'e7': _buildHighlightedSquare(AppColors.secondaryFixed.withOpacity(0.5), text: 'e7', textColor: AppColors.onSecondaryFixedVariant),
              'e6': _buildHighlightedSquare(AppColors.secondaryFixed.withOpacity(0.5), text: 'e6', textColor: AppColors.onSecondaryFixedVariant),
              'e5': _buildHighlightedSquare(AppColors.secondaryFixed.withOpacity(0.5), text: 'e5', textColor: AppColors.onSecondaryFixedVariant),
              'e3': _buildHighlightedSquare(AppColors.secondaryFixed.withOpacity(0.5), text: 'e3', textColor: AppColors.onSecondaryFixedVariant),
              'e2': _buildHighlightedSquare(AppColors.secondaryFixed.withOpacity(0.5), text: 'e2', textColor: AppColors.onSecondaryFixedVariant),
              'e1': _buildHighlightedSquare(AppColors.secondaryFixed.withOpacity(0.5), text: 'e1', textColor: AppColors.onSecondaryFixedVariant),
              
              // Fila 4 (horizontal)
              'a4': _buildHighlightedSquare(AppColors.primary.withOpacity(0.15), text: 'a4', textColor: AppColors.primary),
              'b4': _buildHighlightedSquare(AppColors.primary.withOpacity(0.15), text: 'b4', textColor: AppColors.primary),
              'c4': _buildHighlightedSquare(AppColors.primary.withOpacity(0.15), text: 'c4', textColor: AppColors.primary),
              'd4': _buildHighlightedSquare(AppColors.primary.withOpacity(0.15), text: 'd4', textColor: AppColors.primary),
              'f4': _buildHighlightedSquare(AppColors.primary.withOpacity(0.15), text: 'f4', textColor: AppColors.primary),
              'g4': _buildHighlightedSquare(AppColors.primary.withOpacity(0.15), text: 'g4', textColor: AppColors.primary),
              'h4': _buildHighlightedSquare(AppColors.primary.withOpacity(0.15), text: 'h4', textColor: AppColors.primary),

              // Intersección e4
              'e4': _buildHighlightedSquare(
                AppColors.primary,
                customChild: Stack(
                  children: [
                    Center(
                      child: Container(
                        width: 12,
                        height: 12,
                        decoration: const BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                    Positioned(
                      bottom: 2,
                      right: 2,
                      child: Text(
                        'e4',
                        style: AppTextStyles.telemetrySm.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 10,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            },
          ),
          const SizedBox(height: AppSpacing.spaceSm),

          // Etiqueta ejemplo
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
              child: Wrap(
                alignment: WrapAlignment.center,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 4,
                children: [
                  const Icon(
                    Icons.pin_drop,
                    size: 14,
                    color: AppColors.primary,
                  ),
                  Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: 'Ejemplo: ',
                          style: AppTextStyles.labelSm.copyWith(
                            color: AppColors.onSurfaceVariant,
                          ),
                        ),
                        TextSpan(
                          text: 'Columna e',
                          style: AppTextStyles.labelSm.copyWith(
                            color: AppColors.onSecondaryFixedVariant, // Actualizado para coincidir
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        TextSpan(
                          text: ' + ',
                          style: AppTextStyles.labelSm.copyWith(
                            color: AppColors.onSurfaceVariant,
                          ),
                        ),
                        TextSpan(
                          text: 'Fila 4',
                          style: AppTextStyles.labelSm.copyWith(
                            color: AppColors.primary,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        TextSpan(
                          text: ' = Casilla ',
                          style: AppTextStyles.labelSm.copyWith(
                            color: AppColors.onSurfaceVariant,
                          ),
                        ),
                        TextSpan(
                          text: 'e4',
                          style: AppTextStyles.labelSm.copyWith(
                            color: AppColors.primary,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
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

  Widget _buildHighlightedSquare(Color bgColor, {String? text, Color? textColor, Widget? customChild}) {
    return Container(
      decoration: BoxDecoration(
        color: bgColor,
      ),
      child: customChild ??
          (text != null
              ? Center(
                  child: Text(
                    text,
                    style: AppTextStyles.telemetrySm.copyWith(
                      color: textColor ?? AppColors.onSurface,
                      fontWeight: FontWeight.bold,
                      fontSize: 10,
                    ),
                  ),
                )
              : null),
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
      icon: Icons.swap_horiz,
      title: '8 Filas (Horizontales)',
      subtitle:
          'Se identifican con números del 1 al 8, de abajo hacia arriba.',
      iconColor: AppColors.primary,
      iconBackgroundColor: AppColors.surfaceContainerLow,
      isColumnLayout: true,
    );
  }

  Widget _buildInfoCard2() {
    return LearningInfoCard(
      icon: Icons.swap_vert,
      title: '8 Columnas (Verticales)',
      subtitle:
          'Se identifican con letras de la \'a\' a la \'h\', de izquierda a derecha.',
      iconColor: AppColors.secondary,
      iconBackgroundColor: AppColors.surfaceContainerLow,
      isColumnLayout: true,
    );
  }

  Widget _buildInfoCard3() {
    return LearningInfoCard(
      icon: Icons.my_location,
      title: 'Coordenadas (Casillas)',
      subtitle: 'Cada casilla tiene un nombre único: letra + número (ej. e4, c6).',
      iconColor: AppColors.primary,
      iconBackgroundColor: AppColors.surfaceContainerLow,
      isColumnLayout: true,
    );
  }

  Widget _buildNamingRuleCallout() {
    return InfoCallout(
      icon: Icons.lightbulb,
      title: 'Regla de Nombrado',
      message:
          'Primero siempre se menciona la <strong>letra de la columna</strong> '
          'y después el <strong>número de la fila</strong>. '
          'Por eso decimos casilla <strong>e4</strong>, nunca 4e.',
      iconColor: AppColors.onPrimary,
      iconBackgroundColor: AppColors.primaryContainer,
      titleColor: AppColors.primary,
      backgroundColor: AppColors.primaryContainer.withOpacity(0.1),
    );
  }

  Widget _buildQuickCheck() {
    return QuickCheck(
      title: 'Comprobación rápida',
      message: '',
      richMessage: [
        TextSpan(
          text:
              'En la notación ajedrecística universal, las letras siempre se escriben en minúsculas ',
          style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
        ),
        TextSpan(
          text: 'a1',
          style: AppTextStyles.telemetrySm.copyWith(
            color: AppColors.primary,
            fontWeight: FontWeight.bold,
          ),
        ),
        TextSpan(
          text: ', ',
          style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
        ),
        TextSpan(
          text: 'd4',
          style: AppTextStyles.telemetrySm.copyWith(
            color: AppColors.primary,
            fontWeight: FontWeight.bold,
          ),
        ),
        TextSpan(
          text: ', ',
          style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
        ),
        TextSpan(
          text: 'h8',
          style: AppTextStyles.telemetrySm.copyWith(
            color: AppColors.primary,
            fontWeight: FontWeight.bold,
          ),
        ),
        TextSpan(
          text: '.',
          style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
        ),
      ],
    );
  }
}

class _RanksFilesHeaderDelegate extends SliverPersistentHeaderDelegate {
  final String category;
  final String title;
  final int currentStep;
  final int totalSteps;
  final VoidCallback onBack;
  final String? badgeText;

  _RanksFilesHeaderDelegate({
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