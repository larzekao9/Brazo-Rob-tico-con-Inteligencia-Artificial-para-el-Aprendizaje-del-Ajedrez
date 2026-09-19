import 'package:flutter/material.dart';

import '../../models/learning/learning_models.dart';

/// Mapea [ChapterSymbol] a un widget concreto (icono Material o glifo ♟♞).
///
/// Los modelos son puros (sin Flutter); la presentación visual del símbolo
/// vive acá, reutilizable por nodos, banners y tarjetas.
class ChapterSymbolIcon extends StatelessWidget {
  final ChapterSymbol symbol;
  final Color color;
  final double size;

  const ChapterSymbolIcon({
    super.key,
    required this.symbol,
    required this.color,
    required this.size,
  });

  static const Map<ChapterSymbol, IconData> _material = {
    ChapterSymbol.board: Icons.grid_4x4,
    ChapterSymbol.start: Icons.play_circle_outline,
    ChapterSymbol.checkmate: Icons.flag,
    ChapterSymbol.strategy: Icons.menu_book,
    ChapterSymbol.trophy: Icons.emoji_events,
  };

  static const Map<ChapterSymbol, String> _glifo = {
    ChapterSymbol.queen: '♛',
    ChapterSymbol.knight: '♞',
    ChapterSymbol.capture: '♟',
    ChapterSymbol.pawn: '♟',
  };

  @override
  Widget build(BuildContext context) {
    final icono = _material[symbol];
    if (icono != null) {
      return Icon(icono, size: size, color: color);
    }
    return Text(
      _glifo[symbol] ?? '?',
      style: TextStyle(
        fontSize: size,
        height: 1,
        color: color,
        fontFeatures: const [FontFeature.tabularFigures()],
      ),
    );
  }
}