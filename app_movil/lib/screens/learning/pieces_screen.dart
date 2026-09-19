import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets.dart';

/// Pantalla 2: Las Piezas - Cada pieza y su movimiento
class PiecesScreen extends StatelessWidget {
  static const String routeName = '/learning/pieces';

  const PiecesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surface,
      body: Stack(
        children: [
          CustomScrollView(
            slivers: [
              SliverPersistentHeader(
                pinned: true,
                delegate: _PiecesHeaderDelegate(
                  category: 'FUNDAMENTOS',
                  title: 'Las Piezas',
                  currentStep: 2,
                  totalSteps: 5,
                  onBack: () => context.go('/learning/board-basics'),
                  badgeText: '2 de 5',
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.margin),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Tarjeta principal: ¿Cuántas piezas?
                      _buildMainCard(),
                      const SizedBox(height: AppSpacing.spaceLg),

                      // Tabla de piezas
                      _buildPiecesTable(),
                      const SizedBox(height: AppSpacing.spaceLg),

                      // Callout importante
                      _buildImportantCallout(),
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

          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: LearningBottomNav(
              onPrevious: () => context.go('/learning/board-basics'),
              onNext: () => context.go('/learning/ranks-files'),
              previousLabel: 'Anterior',
              nextLabel: 'Siguiente',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMainCard() {
    return LearningCard(
      padding: AppSpacing.cardPaddingLg,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
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
                    const Text('🎓', style: TextStyle(fontSize: 14)),
                    const SizedBox(width: 4),
                    Text(
                      'Fundamentos',
                      style: AppTextStyles.labelSm.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.spaceSm,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppColors.secondaryFixed.withOpacity(0.3),
                  borderRadius: AppRadius.radiusFull,
                ),
                child: Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: AppColors.secondary,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '16 piezas por bando',
                      style: AppTextStyles.telemetrySm.copyWith(
                        color: AppColors.onSecondaryFixed,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceMd),
          Text(
            '¿Cuántas piezas tiene cada jugador?',
            style: AppTextStyles.headlineMd.copyWith(color: AppColors.onSurface),
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          Text(
            'Las piezas de ajedrez se dividen en claras y oscuras '
            '(<strong>Blancas</strong> y <strong>Negras</strong>). '
            'Cada bando comanda exactamente 16 combatientes organizados en rangos tácticos.',
            style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant),
          ),
        ],
      ),
    );
  }

  Widget _buildPiecesTable() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header de la tabla
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.spaceMd,
            vertical: 12,
          ),
          child: Row(
            children: [
              Expanded(
                flex: 3,
                child: Text(
                  'Blancas',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.left,
                ),
              ),
              Expanded(
                flex: 4,
                child: Text(
                  'Pieza',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.onSurface,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              Expanded(
                flex: 3,
                child: Text(
                  'Negras',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.secondary,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.right,
                ),
              ),
            ],
          ),
        ),

        // Filas de piezas
        Column(
          children: [
            _buildPieceRow(
              pieceName: 'Rey',
              role: 'Pieza Clave',
              count: 1,
              whitePiece: ChessPieceSvg(pieceType: 'king', isWhite: true, size: 40),
              blackPiece: ChessPieceSvg(pieceType: 'king', isWhite: false, size: 40),
            ),
            _buildPieceRow(
              pieceName: 'Dama',
              role: 'Poder Táctico',
              count: 1,
              whitePiece: ChessPieceSvg(pieceType: 'queen', isWhite: true, size: 40),
              blackPiece: ChessPieceSvg(pieceType: 'queen', isWhite: false, size: 40),
            ),
            _buildPieceRow(
              pieceName: 'Torres',
              role: 'Flancos',
              count: 2,
              whitePiece: ChessPieceSvg(pieceType: 'rook', isWhite: true, size: 40),
              blackPiece: ChessPieceSvg(pieceType: 'rook', isWhite: false, size: 40),
            ),
            _buildPieceRow(
              pieceName: 'Alfiles',
              role: 'Diagonales',
              count: 2,
              whitePiece: ChessPieceSvg(pieceType: 'bishop', isWhite: true, size: 40),
              blackPiece: ChessPieceSvg(pieceType: 'bishop', isWhite: false, size: 40),
            ),
            _buildPieceRow(
              pieceName: 'Caballos',
              role: 'Salto en L',
              count: 2,
              whitePiece: ChessPieceSvg(pieceType: 'knight', isWhite: true, size: 40),
              blackPiece: ChessPieceSvg(pieceType: 'knight', isWhite: false, size: 40),
            ),
            _buildPieceRow(
              pieceName: 'Peones',
              role: 'Línea Frontal',
              count: 8,
              whitePiece: ChessPieceSvg(pieceType: 'pawn', isWhite: true, size: 40),
              blackPiece: ChessPieceSvg(pieceType: 'pawn', isWhite: false, size: 40),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPieceRow({
    required String pieceName,
    required String role,
    required int count,
    required Widget whitePiece,
    required Widget blackPiece,
  }) {
    return PieceRow(
      pieceName: pieceName,
      pieceType: pieceName.toLowerCase(),
      count: count,
      role: role,
      whitePiece: whitePiece,
      blackPiece: blackPiece,
    );
  }

  Widget _buildImportantCallout() {
    return InfoCallout(
      icon: Icons.check_circle,
      title: 'IMPORTANTE',
      message:
          'Cada jugador comienza con <strong class="font-semibold">16 piezas</strong>. '
          'En total hay <strong class="font-semibold">32 piezas</strong> sobre el tablero al inicio de la partida.',
      iconColor: AppColors.primary,
      iconBackgroundColor: AppColors.primaryContainer,
      titleColor: AppColors.primary,
    );
  }

  Widget _buildQuickCheck() {
    return QuickCheck(
      title: 'Comprobación rápida',
      message: '',
      richMessage: [
        TextSpan(
          text:
              '1 Rey + 1 Dama + 2 Torres + 2 Alfiles + 2 Caballos + 8 Peones = ',
          style: AppTextStyles.telemetrySm.copyWith(
            color: AppColors.secondary,
            fontWeight: FontWeight.bold,
          ),
        ),
        TextSpan(
          text: '16 piezas',
          style: AppTextStyles.telemetrySm.copyWith(
            color: AppColors.primary,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}

class _PiecesHeaderDelegate extends SliverPersistentHeaderDelegate {
  final String category;
  final String title;
  final int currentStep;
  final int totalSteps;
  final VoidCallback onBack;
  final String? badgeText;

  _PiecesHeaderDelegate({
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