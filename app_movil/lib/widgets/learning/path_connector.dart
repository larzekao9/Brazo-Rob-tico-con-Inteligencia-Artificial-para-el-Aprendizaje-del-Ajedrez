import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../models/learning/learning_models.dart';
import '../../theme/app_colors.dart';

/// Estilo visual de la línea que une dos nodos del camino.
enum PathConnectorStyle {
  /// Ambos nodos completados: línea sólida esmeralda.
  completed,

  /// Nodo completado → nodo en curso: gradiente esmeralda → teal → slate.
  activeLeap,

  /// Nodo en curso → siguiente disponible: guiones slate gruesos.
  upcoming,

  /// Involucra un nodo bloqueado: guiones claros.
  locked,
}

/// Desplazamiento lateral usado por los nodos en los bordes (equivale al
/// padding `left/right` que aplica [LearningPath] a las filas laterales).
const double pathSideOffset = 40;

/// Segmento curvo (S) que conecta dos nodos consecutivos del camino.
///
/// El punto de anclaje horizontal de cada extremo se calcula según la
/// alineación del nodo, para que la curva siempre arranque/termine en el
/// centro de la pieza (coincide con la geometría de [ChapterNode]).
class PathConnector extends StatelessWidget {
  final PathAlignment from;
  final PathAlignment to;
  final PathConnectorStyle style;
  final double height;

  const PathConnector({
    super.key,
    required this.from,
    required this.to,
    required this.style,
    this.height = 72,
  });

  static double _anchorX(PathAlignment alignment, double width) {
    switch (alignment) {
      case PathAlignment.center:
        return width / 2;
      case PathAlignment.left:
        return pathSideOffset + 32; // 32 = radio del nodo estándar
      case PathAlignment.right:
        return width - (pathSideOffset + 32);
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = math.max(constraints.maxWidth, 1.0);
        return SizedBox(
          height: height,
          width: double.infinity,
          child: CustomPaint(
            painter: _PathConnectorPainter(
              style: style,
              fromXFactor: _anchorX(from, w) / w,
              toXFactor: _anchorX(to, w) / w,
            ),
          ),
        );
      },
    );
  }
}

class _PathConnectorPainter extends CustomPainter {
  final PathConnectorStyle style;
  final double fromXFactor;
  final double toXFactor;

  const _PathConnectorPainter({
    required this.style,
    required this.fromXFactor,
    required this.toXFactor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final fromX = fromXFactor * size.width;
    final toX = toXFactor * size.width;
    const top = 6.0;
    final bottom = size.height - 6.0;
    final mid = size.height / 2;

    final path = Path()
      ..moveTo(fromX, top)
      ..cubicTo(fromX, mid, toX, mid, toX, bottom);

    switch (style) {
      case PathConnectorStyle.completed:
        _stroke(canvas, path, [
          AppColors.primary,
          const Color(0xFF006446),
        ], width: 4, dash: null);
      case PathConnectorStyle.activeLeap:
        _stroke(canvas, path, [
          AppColors.primary,
          const Color(0xFF006875),
        ], width: 4, dash: null);
      case PathConnectorStyle.upcoming:
        _stroke(canvas, path, const [
          AppColors.outlineVariant,
          AppColors.outlineVariant,
        ], width: 3, dash: const [7, 7]);
      case PathConnectorStyle.locked:
        _stroke(canvas, path, const [
          AppColors.surfaceContainerHigh,
          AppColors.surfaceContainerHigh,
        ], width: 3, dash: const [5, 5]);
    }
  }

  void _stroke(
    Canvas canvas,
    Path path,
    List<Color> colors, {
    required double width,
    required List<double>? dash,
  }) {
    final bounds = path.getBounds();
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = width
      ..strokeCap = StrokeCap.round
      ..shader = ui.Gradient.linear(
        Offset(bounds.center.dx, bounds.top),
        Offset(bounds.center.dx, bounds.bottom),
        colors,
      );

    if (dash == null) {
      canvas.drawPath(path, paint);
      return;
    }

    final metrics = path.computeMetrics();
    for (final metric in metrics) {
      var distance = 0.0;
      while (distance < metric.length) {
        final next = math.min(distance + dash[0], metric.length);
        final tangent = metric.getTangentForOffset(distance);
        if (tangent == null) break;
        final delta = metric.getTangentForOffset(next);
        canvas.drawLine(tangent.position, delta?.position ?? tangent.position, paint);
        distance += dash[0] + dash[1];
      }
    }
  }

  @override
  bool shouldRepaint(covariant _PathConnectorPainter oldDelegate) {
    return oldDelegate.style != style ||
        oldDelegate.fromXFactor != fromXFactor ||
        oldDelegate.toXFactor != toXFactor;
  }
}