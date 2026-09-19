import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';

/// Widget principal de una tarjeta de aprendizaje con estilo glassmorphism
class LearningCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? backgroundColor;
  final List<BoxShadow>? shadows;
  final Border? border;
  final VoidCallback? onTap;

  const LearningCard({
    super.key,
    required this.child,
    this.padding,
    this.backgroundColor,
    this.shadows,
    this.border,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final card = Container(
      padding: padding ?? AppSpacing.cardPadding,
      decoration: BoxDecoration(
        color: backgroundColor ?? AppColors.surfaceContainerLowest,
        borderRadius: AppRadius.radiusLg,
        border: border ?? Border.all(color: AppColors.outlineVariant, width: 1),
        boxShadow: shadows ??
            [
              BoxShadow(
                color: Colors.black.withOpacity(0.04),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
      ),
      child: child,
    );

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: AppRadius.radiusLg,
        child: card,
      );
    }
    return card;
  }
}

/// Tarjeta educativa con icono, título y subtítulo (estilo 3-columnas)
class LearningInfoCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color iconColor;
  final Color iconBackgroundColor;
  final bool isColumnLayout;

  const LearningInfoCard({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.iconColor,
    required this.iconBackgroundColor,
    this.isColumnLayout = false,
  });

  @override
  Widget build(BuildContext context) {
    final iconWidget = Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: iconBackgroundColor,
        borderRadius: AppRadius.radiusLg,
      ),
      child: Icon(icon, size: 22, color: iconColor),
    );

    final textWidget = Column(
      crossAxisAlignment:
          isColumnLayout ? CrossAxisAlignment.center : CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          title,
          style: AppTextStyles.headlineSm.copyWith(color: AppColors.onSurface),
          textAlign: isColumnLayout ? TextAlign.center : TextAlign.left,
        ),
        const SizedBox(height: AppSpacing.spaceXs),
        Text(
          subtitle,
          style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
          textAlign: isColumnLayout ? TextAlign.center : TextAlign.left,
        ),
      ],
    );

    if (isColumnLayout) {
      return LearningCard(
        padding: AppSpacing.cardPadding,
        child: SizedBox(
          width: double.infinity,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              iconWidget,
              const SizedBox(height: AppSpacing.spaceSm),
              textWidget,
            ],
          ),
        ),
      );
    }

    return LearningCard(
      padding: AppSpacing.cardPaddingSm,
      child: Row(
        children: [
          iconWidget,
          const SizedBox(width: AppSpacing.spaceSm),
          Expanded(child: textWidget),
        ],
      ),
    );
  }
}

/// Texto que interpreta etiquetas `<strong>...</strong>` (heredadas del
/// mockup web) y las dibuja en negrita en vez de mostrar el HTML crudo.
/// Las clases `class="..."` dentro de la etiqueta se ignoran.
class MarkupText extends StatelessWidget {
  final String text;
  final TextStyle? style;
  final TextStyle? strongStyle;
  final TextAlign textAlign;

  const MarkupText(
    this.text, {
    super.key,
    this.style,
    this.strongStyle,
    this.textAlign = TextAlign.start,
  });

  static final _strongPattern = RegExp(
    r'<strong[^>]*>(.*?)</strong>',
    caseSensitive: false,
    dotAll: true,
  );

  @override
  Widget build(BuildContext context) {
    final baseStyle = style ?? DefaultTextStyle.of(context).style;
    final boldStyle = (strongStyle ?? baseStyle).copyWith(
      fontWeight: FontWeight.bold,
    );

    if (!_strongPattern.hasMatch(text)) {
      return Text(text, style: baseStyle, textAlign: textAlign);
    }

    final spans = <InlineSpan>[];
    var cursor = 0;
    for (final match in _strongPattern.allMatches(text)) {
      if (match.start > cursor) {
        spans.add(TextSpan(
          text: text.substring(cursor, match.start),
          style: baseStyle,
        ));
      }
      spans.add(TextSpan(text: match.group(1), style: boldStyle));
      cursor = match.end;
    }
    if (cursor < text.length) {
      spans.add(TextSpan(text: text.substring(cursor), style: baseStyle));
    }

    return Text.rich(
      TextSpan(children: spans),
      textAlign: textAlign,
    );
  }
}

/// Callout importante con icono y mensaje (estilo verde esmeralda)
class InfoCallout extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final Color backgroundColor;
  final Color iconColor;
  final Color iconBackgroundColor;
  final Color titleColor;

  const InfoCallout({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.backgroundColor = const Color(0x1A087F5B), // primaryContainer/10
    this.iconColor = AppColors.primary,
    this.iconBackgroundColor = AppColors.primaryContainer,
    this.titleColor = AppColors.primary,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: AppSpacing.cardPaddingMd,
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: AppRadius.radiusLg,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: iconBackgroundColor,
              borderRadius: AppRadius.radiusFull,
            ),
            child: Icon(icon, size: 20, color: iconColor),
          ),
          const SizedBox(width: AppSpacing.spaceSm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTextStyles.labelMd.copyWith(
                    color: titleColor,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 4),
                MarkupText(
                  message,
                  style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Sección de "Comprobación rápida" / Tip Pro
class QuickCheck extends StatelessWidget {
  final String title;
  final String message;
  final String? tipLabel;
  final List<InlineSpan>? richMessage;

  const QuickCheck({
    super.key,
    required this.title,
    required this.message,
    this.tipLabel = 'Tip Pro',
    this.richMessage,
  });

  @override
  Widget build(BuildContext context) {
    return LearningCard(
      padding: AppSpacing.cardPaddingMd,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  title,
                  style: AppTextStyles.labelMd.copyWith(
                    color: AppColors.onSurface,
                    fontWeight: FontWeight.bold,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (tipLabel != null)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.1),
                    borderRadius: AppRadius.radiusFull,
                  ),
                  child: Text(
                    tipLabel!,
                    style: AppTextStyles.labelSm.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceXs),
          richMessage != null
              ? Text.rich(
                  TextSpan(children: richMessage!),
                  style: AppTextStyles.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                )
              : Text(
                  message,
                  style: AppTextStyles.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
        ],
      ),
    );
  }
}

/// Header con progreso para pantallas de aprendizaje
class LearningProgressHeader extends StatelessWidget {
  final String category;
  final String title;
  final int currentStep;
  final int totalSteps;
  final VoidCallback onBack;
  final String? badgeText;
  final Color? badgeColor;

  const LearningProgressHeader({
    super.key,
    required this.category,
    required this.title,
    required this.currentStep,
    required this.totalSteps,
    required this.onBack,
    this.badgeText,
    this.badgeColor,
  });

  @override
  Widget build(BuildContext context) {
    final progress = currentStep / totalSteps;

    return SafeArea(
      top: true,
      bottom: false,
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
                      color: (badgeColor ?? AppColors.primary).withOpacity(0.1),
                      borderRadius: AppRadius.radiusFull,
                      border: Border.all(
                        color: (badgeColor ?? AppColors.primary).withOpacity(0.3),
                      ),
                    ),
                    child: Text(
                      badgeText!,
                      style: AppTextStyles.telemetrySm.copyWith(
                        color: badgeColor ?? AppColors.primary,
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
              valueColor: AlwaysStoppedAnimation<Color>(
                badgeColor ?? AppColors.primary,
              ),
              minHeight: 4,
              borderRadius: AppRadius.radiusFull,
            ),
          ],
        ),
      ),
    );
  }
}

/// Barra de navegación inferior (Anterior / Siguiente)
class LearningBottomNav extends StatelessWidget {
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;
  final String previousLabel;
  final String nextLabel;
  final bool isLast;

  const LearningBottomNav({
    super.key,
    this.onPrevious,
    this.onNext,
    this.previousLabel = 'Anterior',
    this.nextLabel = 'Siguiente',
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      bottom: true,
      child: Container(
        height: 72,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.margin,
          vertical: AppSpacing.spaceSm,
        ),
        decoration: BoxDecoration(
          color: AppColors.surfaceContainerLowest.withOpacity(0.95),
          border: Border(
            top: BorderSide(color: AppColors.outlineVariant, width: 1),
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 44,
                child: OutlinedButton(
                  onPressed: onPrevious,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.primary,
                    side: const BorderSide(color: AppColors.primary, width: 1.5),
                    shape: RoundedRectangleBorder(
                      borderRadius: AppRadius.radiusLg,
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    textStyle: AppTextStyles.labelMd.copyWith(
                      color: AppColors.primary,
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.arrow_back, size: 18),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          previousLabel,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.gutter),
            Expanded(
              child: SizedBox(
                height: 44,
                child: FilledButton(
                  onPressed: onNext,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.primaryContainer,
                    foregroundColor: AppColors.onPrimaryContainer,
                    shape: RoundedRectangleBorder(
                      borderRadius: AppRadius.radiusLg,
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    textStyle: AppTextStyles.labelMd.copyWith(
                      color: AppColors.onPrimaryContainer,
                    ),
                    elevation: 0,
                    shadowColor: Colors.transparent,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Flexible(
                        child: Text(
                          isLast ? 'Comenzar' : nextLabel,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Icon(Icons.arrow_forward, size: 18),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Tablero de ajedrez interactivo 8x8 con coordenadas
class InteractiveChessBoard extends StatelessWidget {
  final Map<String, Widget>? highlightedSquares;
  final Map<String, String>? squareLabels;
  final bool showCoordinates;
  final double? maxSize;
  final VoidCallback? onSquareTap;
  final String? Function(int row, int col)? squareIdBuilder;

  const InteractiveChessBoard({
    super.key,
    this.highlightedSquares,
    this.squareLabels,
    this.showCoordinates = true,
    this.maxSize = 340,
    this.onSquareTap,
    this.squareIdBuilder,
  });

  @override
  Widget build(BuildContext context) {
    final files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
    final ranks = [8, 7, 6, 5, 4, 3, 2, 1];

    return LayoutBuilder(
      builder: (context, constraints) {
        final boardSize =
            (constraints.maxWidth < (maxSize ?? 340))
                ? constraints.maxWidth
                : (maxSize ?? 340);
        final squareSize = boardSize / 8;

        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showCoordinates)
              _buildCoordinatesRow(files, boardSize, squareSize),
            SizedBox(
              width: boardSize,
              height: boardSize,
              child: Stack(
                children: [
                  // Board grid
                  Column(
                    children: List.generate(8, (rankIndex) {
                      final rank = ranks[rankIndex];
                      return Expanded(
                        child: Row(
                          children: List.generate(8, (fileIndex) {
                            final file = files[fileIndex];
                            final isLight = (rankIndex + fileIndex) % 2 == 0;
                            final squareId = '$file$rank';
                            final isHighlighted =
                                highlightedSquares?.containsKey(squareId) ?? false;

                            return _buildSquare(
                              size: squareSize,
                              isLight: isLight,
                              isHighlighted: isHighlighted,
                              highlightWidget: highlightedSquares?[squareId],
                              label: squareLabels?[squareId],
                              rank: rank,
                              file: file,
                              // Las letras a-h ya van en las filas externas de
                              // coordenadas; dentro solo los números de fila.
                              showFileLabel: false,
                              showRankLabel: fileIndex == 0 && showCoordinates,
                              onTap: onSquareTap != null
                                  ? () => onSquareTap!()
                                  : null,
                            );
                          }),
                        ),
                      );
                    }),
                  ),
                ],
              ),
            ),
            if (showCoordinates)
              _buildCoordinatesRow(files, boardSize, squareSize),
          ],
        );
      },
    );
  }

  Widget _buildCoordinatesRow(
      List<String> files, double boardSize, double squareSize) {
    return SizedBox(
      width: boardSize,
      height: 24,
      child: Row(
        children: files.map((file) {
          return SizedBox(
            width: squareSize,
            child: Center(
              child: Text(
                file,
                style: AppTextStyles.telemetrySm.copyWith(
                  color: AppColors.outline,
                  fontSize: 10,
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildSquare({
    required double size,
    required bool isLight,
    required bool isHighlighted,
    Widget? highlightWidget,
    String? label,
    required int rank,
    required String file,
    required bool showFileLabel,
    required bool showRankLabel,
    VoidCallback? onTap,
  }) {
    final baseColor = isLight
        ? AppColors.chessWhiteSquare
        : AppColors.chessBlackSquare;

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: size,
        height: size,
        color: isHighlighted
            ? AppColors.secondaryFixed.withOpacity(0.5)
            : baseColor,
        child: Stack(
          alignment: Alignment.center,
          children: [
            if (highlightWidget != null) highlightWidget,
            if (label != null)
              Center(
                child: Text(
                  label,
                  style: AppTextStyles.telemetrySm.copyWith(
                    color: AppColors.secondary,
                    fontWeight: FontWeight.bold,
                    fontSize: 10,
                  ),
                ),
              ),
            if (showRankLabel)
              Positioned(
                top: 2,
                left: 2,
                child: Text(
                  '$rank',
                  style: AppTextStyles.telemetrySm.copyWith(
                    color: AppColors.outline,
                    fontSize: 9,
                  ),
                ),
              ),
            if (showFileLabel)
              Positioned(
                bottom: 2,
                right: 2,
                child: Text(
                  file,
                  style: AppTextStyles.telemetrySm.copyWith(
                    color: AppColors.outline,
                    fontSize: 9,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Fila de pieza para la lista de piezas (Blancas | Pieza | Negras)
class PieceRow extends StatelessWidget {
  final String pieceName;
  final String pieceType; // 'king', 'queen', 'rook', 'bishop', 'knight', 'pawn'
  final int count;
  final String role;
  final Widget whitePiece;
  final Widget blackPiece;

  const PieceRow({
    super.key,
    required this.pieceName,
    required this.pieceType,
    required this.count,
    required this.role,
    required this.whitePiece,
    required this.blackPiece,
  });

  @override
  Widget build(BuildContext context) {
    return LearningCard(
      padding: AppSpacing.cardPaddingSm,
      child: Row(
        children: [
          // Blancas
          Expanded(
            flex: 3,
            child: Row(
              children: [
                whitePiece,
                const SizedBox(width: AppSpacing.spaceSm),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainerHigh,
                    borderRadius: AppRadius.radiusFull,
                  ),
                  child: Text(
                    '${count}x',
                    style: AppTextStyles.telemetrySm.copyWith(
                      color: AppColors.secondary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Nombre
          Expanded(
            flex: 4,
            child: Column(
              children: [
                Text(
                  pieceName,
                  style: AppTextStyles.headlineSm.copyWith(
                    color: AppColors.onSurface,
                  ),
                ),
                Text(
                  role,
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.onSurfaceVariant,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ),
          // Negras
          Expanded(
            flex: 3,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainerHigh,
                    borderRadius: AppRadius.radiusFull,
                  ),
                  child: Text(
                    '${count}x',
                    style: AppTextStyles.telemetrySm.copyWith(
                      color: AppColors.secondary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.spaceSm),
                blackPiece,
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Pieza de ajedrez SVG widget
class ChessPieceSvg extends StatelessWidget {
  final String pieceType; // 'king', 'queen', 'rook', 'bishop', 'knight', 'pawn'
  final bool isWhite;
  final double size;

  const ChessPieceSvg({
    super.key,
    required this.pieceType,
    required this.isWhite,
    this.size = 40,
  });

  @override
  Widget build(BuildContext context) {
    final svg = _getSvg(pieceType);
    // Piezas blancas: ícono oscuro sobre fondo claro.
    // Piezas negras: ícono blanco sobre fondo oscuro + borde blanco para contraste.
    final iconColor = isWhite ? AppColors.onSurface : Colors.white;

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: isWhite ? AppColors.surfaceContainer : AppColors.inverseSurface,
        borderRadius: AppRadius.radiusLg,
        border: isWhite
            ? null
            : Border.all(color: Colors.white.withOpacity(0.55), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: isWhite
                ? AppColors.primary.withOpacity(0.35)
                : Colors.black.withOpacity(0.45),
            blurRadius: isWhite ? 2 : 3,
            offset: Offset(0, isWhite ? 1 : 2),
          ),
        ],
      ),
      child: Center(
        child: Transform.translate(
          offset: Offset(0, -size * 0.08), // Compensar el margen inferior de la fuente
          child: Text(
            svg,
            style: TextStyle(
              fontSize: size * 0.65,
              color: iconColor,
              fontWeight: FontWeight.bold,
              shadows: [
                Shadow(
                  color: isWhite
                      ? AppColors.primary.withOpacity(0.35)
                      : Colors.white.withOpacity(0.25),
                  blurRadius: 2,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _getSvg(String type) {
    switch (type) {
      case 'king':
        return '♔';
      case 'queen':
        return '♕';
      case 'rook':
        return '♖';
      case 'bishop':
        return '♗';
      case 'knight':
        return '♘';
      case 'pawn':
        return '♙';
      default:
        return '?';
    }
  }
}

/// Contador de piezas (1 Rey + 1 Dama + 2 Torres...)
class PieceCountSummary extends StatelessWidget {
  final List<PieceCountItem> items;

  const PieceCountSummary({
    super.key,
    required this.items,
  });

  @override
  Widget build(BuildContext context) {
    return LearningCard(
      padding: AppSpacing.cardPaddingMd,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.calculate,
                size: 18,
                color: AppColors.secondary,
              ),
              const SizedBox(width: AppSpacing.spaceXs),
              Text(
                'Comprobación rápida',
                style: AppTextStyles.labelMd.copyWith(
                  color: AppColors.onSurface,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: AppRadius.radiusFull,
                ),
                child: Text(
                  'Tip Pro',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceSm),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: items.map((item) {
                return Padding(
                  padding: const EdgeInsets.only(right: AppSpacing.spaceSm),
                  child: Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: item.count > 1 ? '${item.count} ' : '',
                          style: AppTextStyles.telemetrySm.copyWith(
                            color: AppColors.secondary,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        TextSpan(
                          text: item.name,
                          style: AppTextStyles.telemetrySm.copyWith(
                            color: AppColors.onSurface,
                          ),
                        ),
                        if (item != items.last)
                          TextSpan(
                            text: ' + ',
                            style: AppTextStyles.telemetrySm.copyWith(
                              color: AppColors.onSurfaceVariant,
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: AppSpacing.spaceXs),
          Text(
            ' = ${items.fold<int>(0, (sum, item) => sum + item.count)} piezas',
            style: AppTextStyles.telemetrySm.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

class PieceCountItem {
  final String name;
  final int count;

  const PieceCountItem({required this.name, required this.count});
}

/// Regla de oro (callout estilo emerald)
class GoldenRuleCallout extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final Color iconColor;
  final Color iconBackgroundColor;

  const GoldenRuleCallout({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.iconColor = AppColors.primary,
    this.iconBackgroundColor = AppColors.primaryContainer,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: AppSpacing.cardPaddingMd,
      decoration: BoxDecoration(
        color: AppColors.primaryContainer.withOpacity(0.1),
        borderRadius: AppRadius.radiusLg,
        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: iconBackgroundColor,
              borderRadius: AppRadius.radiusFull,
            ),
            child: Icon(icon, size: 20, color: iconColor),
          ),
          const SizedBox(width: AppSpacing.spaceSm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTextStyles.labelMd.copyWith(
                    color: AppColors.primary,
                    letterSpacing: 0.5,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                MarkupText(
                  message,
                  style: AppTextStyles.bodyMd.copyWith(color: AppColors.onSurfaceVariant),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Sección de Movimiento vs Captura
class MoveVsCaptureSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.spaceXs),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Movimiento y captura',
                style: AppTextStyles.headlineSm.copyWith(
                  color: AppColors.onSurface,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                'Diferencia fundamental de las acciones sobre el tablero',
                style: AppTextStyles.bodySm.copyWith(color: AppColors.outline),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.spaceSm),
        // Movimiento
        Container(
          padding: AppSpacing.cardPaddingMd,
          decoration: BoxDecoration(
            color: const Color(0xFFEFF6FF), // blue-50
            borderRadius: AppRadius.radiusXl,
            border: Border.all(color: const Color(0xCCBFDBFE)), // blue-200
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: const Color(0xFFDBEAFE), // blue-100
                      borderRadius: AppRadius.radiusLg,
                    ),
                    child: const Icon(
                      Icons.pan_tool_alt,
                      size: 18,
                      color: Color(0xFF1E40AF), // blue-800
                    ),
                  ),
                  const SizedBox(width: AppSpacing.spaceSm),
                  Text(
                    'Movimiento',
                    style: AppTextStyles.headlineSm.copyWith(
                      color: const Color(0xFF1E3A8A), // blue-950
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.spaceSm),
              Text(
                'Es el traslado de una pieza de ajedrez desde su casilla actual a otra casilla totalmente desocupada siguiendo su regla particular de avance.',
                style: AppTextStyles.bodySm.copyWith(
                  color: const Color(0xFF374151), // slate-700
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.spaceSm),
        // Captura
        Container(
          padding: AppSpacing.cardPaddingMd,
          decoration: BoxDecoration(
            color: const Color(0xFFFFF7ED), // amber-50
            borderRadius: AppRadius.radiusXl,
            border: Border.all(color: const Color(0x99FCD34D)), // amber-200
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEF3C7), // amber-100
                      borderRadius: AppRadius.radiusLg,
                    ),
                    child: const Icon(
                      Icons.close,
                      size: 18,
                      color: Color(0xFF92400E), // amber-800
                    ),
                  ),
                  const SizedBox(width: AppSpacing.spaceSm),
                  Text(
                    'Captura',
                    style: AppTextStyles.headlineSm.copyWith(
                      color: const Color(0xFF78350F), // amber-950
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.spaceSm),
              Text(
                'Consiste en retirar una pieza rival del tablero y ocupar su casilla exacta con la pieza atacante.',
                style: AppTextStyles.bodySm.copyWith(
                  color: const Color(0xFF374151), // slate-700
                ),
              ),
              const SizedBox(height: AppSpacing.spaceXs),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFFFDF2F8), // rose-50
                  borderRadius: AppRadius.radiusLg,
                  border: Border.all(color: const Color(0x99F43F5E)), // rose-150
                ),
                child: Text(
                  '*(Nunca es posible capturar una pieza propia)',
                  style: AppTextStyles.labelSm.copyWith(
                    color: const Color(0xFFBE123C), // rose-700
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Consejo final (estilo emerald)
class FinalAdviceCallout extends StatelessWidget {
  final String title;
  final String message;

  const FinalAdviceCallout({
    super.key,
    required this.title,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: AppSpacing.cardPaddingMd,
      decoration: BoxDecoration(
        color: const Color(0xFFECFDF5), // emerald-50
        borderRadius: AppRadius.radiusXl,
        border: Border.all(color: const Color(0xCCA7F3D0)), // emerald-200
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: const Color(0xFFD1FAE5), // emerald-100
              borderRadius: AppRadius.radiusFull,
            ),
            child: const Icon(
              Icons.lightbulb,
              size: 20,
              color: Color(0xFF065F46), // emerald-800
            ),
          ),
          const SizedBox(width: AppSpacing.spaceSm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTextStyles.headlineSm.copyWith(
                    color: const Color(0xFF064E3B), // emerald-950
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  message,
                  style: AppTextStyles.bodySm.copyWith(
                    color: const Color(0xFF065F46), // emerald-800
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