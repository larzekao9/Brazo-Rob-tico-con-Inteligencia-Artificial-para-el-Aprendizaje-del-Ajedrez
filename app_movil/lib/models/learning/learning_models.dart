/// Modelos de dominio del módulo de aprendizaje ("Camino de Maestría").
///
/// Archivo intencionalmente sin imports de Flutter: la capa de negocio se
/// puede probar en aislamiento (Dart puro) y los widgets deciden cómo
/// presentar estas entidades.
library;

/// Estado de un capítulo dentro del camino de aprendizaje.
enum ChapterStatus { completed, inProgress, available, locked }

/// Desplazamiento horizontal de un nodo en el camino (péndulo S).
///
/// Determina la geometría del camino: los nodos alternan entre los bordes y
/// el centro para dibujar una "S" vertical.
enum PathAlignment { left, center, right }

/// Referencia presentacional del símbolo de un capítulo/unidad.
///
/// Se guarda como enum (no como `IconData`) para que los modelos sigan
/// libres de Flutter; la capa de widgets lo mapea a iconos o glifos.
enum ChapterSymbol {
  board,
  queen,
  start,
  knight,
  capture,
  checkmate,
  strategy,
  trophy,
  pawn,
}

/// Capítulo de aprendizaje (dato intrínseco, no cambia con el progreso).
class LearningChapter {
  final String id;
  final String title;
  final String subtitle;
  final String? description;
  final ChapterSymbol symbol;
  final PathAlignment alignment;
  final bool isBoss;
  final int xp;
  final int stepsTotal;

  /// Ruta GoRouter a la pantalla de la lección. `null` = lección aún
  /// no implementada (se muestra "Próximamente").
  final String? route;

  const LearningChapter({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.symbol,
    required this.alignment,
    required this.xp,
    required this.stepsTotal,
    this.description,
    this.isBoss = false,
    this.route,
  });
}

/// Unidad (bloque) del camino de aprendizaje: agrupa varios capítulos.
class LearningUnit {
  final String id;
  final String title;
  final String description;
  final String badgeLabel;
  final ChapterSymbol symbol;
  final List<LearningChapter> chapters;

  const LearningUnit({
    required this.id,
    required this.title,
    required this.description,
    required this.badgeLabel,
    required this.symbol,
    required this.chapters,
  });
}

/// Progreso del jugador dentro del camino. Inmutable; se actualiza con
/// `copyWith` desde la capa de servicio/controlador.
class LearningProgress {
  /// Cantidad de capítulos completados (los primeros N de la lista).
  final int completedChapters;

  /// Índice del capítulo en curso (el primero no completado).
  final int activeChapterIndex;

  /// Pasos/lecciones completados dentro del capítulo en curso.
  final int activeChapterSteps;

  final int xp;
  final int streakDays;
  final int nivel;
  final String rankLabel;

  const LearningProgress({
    required this.completedChapters,
    required this.activeChapterIndex,
    required this.activeChapterSteps,
    required this.xp,
    required this.streakDays,
    required this.nivel,
    required this.rankLabel,
  });

  /// Progreso inicial de demostración (coincide con el mockup del camino).
  factory LearningProgress.inicial() => const LearningProgress(
        completedChapters: 3,
        activeChapterIndex: 3,
        activeChapterSteps: 3,
        xp: 350,
        streakDays: 3,
        nivel: 4,
        rankLabel: 'Aprendiz Táctico',
      );

  LearningProgress copyWith({
    int? completedChapters,
    int? activeChapterIndex,
    int? activeChapterSteps,
    int? xp,
    int? streakDays,
    int? nivel,
    String? rankLabel,
  }) {
    return LearningProgress(
      completedChapters: completedChapters ?? this.completedChapters,
      activeChapterIndex: activeChapterIndex ?? this.activeChapterIndex,
      activeChapterSteps: activeChapterSteps ?? this.activeChapterSteps,
      xp: xp ?? this.xp,
      streakDays: streakDays ?? this.streakDays,
      nivel: nivel ?? this.nivel,
      rankLabel: rankLabel ?? this.rankLabel,
    );
  }
}

/// Capítulo listo para presentar: junta el dato intrínseco con el estado
/// derivado del progreso.
class ResolvedChapter {
  final LearningChapter chapter;
  final ChapterStatus status;

  /// Pasos efectivamente completados (total para `completed`,
  /// parcial para `inProgress`, 0 en el resto).
  final int stepsDone;

  const ResolvedChapter({
    required this.chapter,
    required this.status,
    required this.stepsDone,
  });
}