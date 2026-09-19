import 'package:flutter/material.dart';

import '../../models/learning/learning_models.dart';
import 'chapter_node.dart';
import 'path_connector.dart';

/// Galería de aprendizaje con geometría de péndulo "S".
///
/// Renderiza la lista de capítulos como nodos que alternan entre los bordes
/// y el centro, conectados por curvas cuyo estilo depende del estado de cada
/// par. Es dinámico: dado cualquier `List<ResolvedChapter>` dibuja el camino.
class LearningPath extends StatelessWidget {
  final List<ResolvedChapter> chapters;
  final ValueChanged<ResolvedChapter> onChapterTap;
  final ValueChanged<ResolvedChapter> onContinueLesson;

  const LearningPath({
    super.key,
    required this.chapters,
    required this.onChapterTap,
    required this.onContinueLesson,
  });

  static PathConnectorStyle _edgeStyle(ResolvedChapter from, ResolvedChapter to) {
    if (from.status == ChapterStatus.completed &&
        to.status == ChapterStatus.completed) {
      return PathConnectorStyle.completed;
    }
    if (from.status == ChapterStatus.completed &&
        to.status == ChapterStatus.inProgress) {
      return PathConnectorStyle.activeLeap;
    }
    if (from.status == ChapterStatus.inProgress &&
        to.status == ChapterStatus.available) {
      return PathConnectorStyle.upcoming;
    }
    return PathConnectorStyle.locked;
  }

  @override
  Widget build(BuildContext context) {
    final filas = <Widget>[];
    for (var i = 0; i < chapters.length; i++) {
      final cap = chapters[i];
      filas.add(
        _NodeRow(
          resolved: cap,
          onTap: () => onChapterTap(cap),
        ),
      );
      if (cap.status == ChapterStatus.inProgress) {
        filas.add(const SizedBox(height: 20));
        filas.add(
          ActiveChapterCard(
            resolved: cap,
            onContinue: () => onContinueLesson(cap),
          ),
        );
      }
      if (i < chapters.length - 1) {
        filas.add(
          PathConnector(
            from: cap.chapter.alignment,
            to: chapters[i + 1].chapter.alignment,
            style: _edgeStyle(cap, chapters[i + 1]),
          ),
        );
      }
    }

    return Stack(
      clipBehavior: Clip.none,
      children: [
        ..._particulasDecorativas(),
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: filas,
        ),
      ],
    );
  }

  List<Widget> _particulasDecorativas() {
    return [
      const Positioned(
        top: 220,
        left: 20,
        child: IgnorePointer(
          child: _Particle(
            glyph: '♟',
            color: Color(0x33087F5B),
            size: 24,
          ),
        ),
      ),
      const Positioned(
        top: 680,
        left: 30,
        child: IgnorePointer(
          child: _Particle(
            glyph: '♝',
            color: Color(0x4D00DAF3),
            size: 22,
          ),
        ),
      ),
      const Positioned(
        top: 980,
        right: 24,
        child: IgnorePointer(
          child: _Particle(
            glyph: '♜',
            color: _aurantina,
            size: 24,
          ),
        ),
      ),
    ];
  }
}

const Color _aurantina = Color(0x66BDC9C1);

class _Particle extends StatelessWidget {
  final String glyph;
  final Color color;
  final double size;

  const _Particle({
    required this.glyph,
    required this.color,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    return Text(
      glyph,
      style: TextStyle(fontSize: size, height: 1, color: color),
    );
  }
}

class _NodeRow extends StatelessWidget {
  final ResolvedChapter resolved;
  final VoidCallback onTap;

  const _NodeRow({required this.resolved, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final alignment = resolved.chapter.alignment;

    final EdgeInsets padding = switch (alignment) {
      PathAlignment.left => const EdgeInsets.only(left: pathSideOffset),
      PathAlignment.right => const EdgeInsets.only(right: pathSideOffset),
      PathAlignment.center => EdgeInsets.zero,
    };

    final AlignmentDirectional alineacion = switch (alignment) {
      PathAlignment.center => AlignmentDirectional.center,
      PathAlignment.left => AlignmentDirectional.centerStart,
      PathAlignment.right => AlignmentDirectional.centerEnd,
    };

    final CrossAxisAlignment cross = switch (alignment) {
      PathAlignment.center => CrossAxisAlignment.center,
      PathAlignment.left => CrossAxisAlignment.start,
      PathAlignment.right => CrossAxisAlignment.end,
    };

    return Padding(
      padding: padding,
      child: Align(
        alignment: alineacion,
        child: Column(
          crossAxisAlignment: cross,
          mainAxisSize: MainAxisSize.min,
          children: [
            ChapterNode(
              resolved: resolved,
              onTap: onTap,
            ),
          ],
        ),
      ),
    );
  }
}