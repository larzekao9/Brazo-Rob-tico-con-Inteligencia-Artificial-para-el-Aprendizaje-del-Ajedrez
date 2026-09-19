import '../../models/learning/learning_models.dart';

/// Catálogo del camino de aprendizaje y lógica de negocio del módulo.
///
/// Responsabilidades:
/// - Definir la unidades/capítulos del camino (dato fuente).
/// - Derivar (a partir del [LearningProgress]) el estado de cada capítulo,
///   el porcentaje global, la cantidad de lecciones pendientes, etc.
///
/// No depende de Flutter ni de la pantalla: se puede probar en aislamiento.
class LearningService {
  const LearningService();

  /// Unidad "Fundamentos y Táctica Inicial" (demo inicial del camino).
  LearningUnit unidadInicial() {
    return const LearningUnit(
      id: 'u1-fundamentos',
      title: 'Unidad 1: Fundamentos y Táctica Inicial',
      description: 'Stockfish Neural IA calibra cada paso táctico',
      badgeLabel: 'EN PROGRESO',
      symbol: ChapterSymbol.pawn,
      chapters: [
        LearningChapter(
          id: 'cap-1-tablero',
          title: 'El tablero',
          subtitle: 'Capítulo 1',
          symbol: ChapterSymbol.board,
          alignment: PathAlignment.center,
          xp: 40,
          stepsTotal: 4,
          route: '/learning/board-basics',
        ),
        LearningChapter(
          id: 'cap-2-piezas',
          title: 'Las piezas',
          subtitle: 'Capítulo 2',
          symbol: ChapterSymbol.queen,
          alignment: PathAlignment.left,
          xp: 45,
          stepsTotal: 4,
          route: '/learning/pieces',
        ),
        LearningChapter(
          id: 'cap-3-inicial',
          title: 'Posición inicial',
          subtitle: 'Capítulo 3',
          symbol: ChapterSymbol.start,
          alignment: PathAlignment.right,
          xp: 45,
          stepsTotal: 4,
          route: '/learning/ranks-files',
        ),
        LearningChapter(
          id: 'cap-4-movimiento',
          title: 'Movimiento de las piezas',
          subtitle: 'Capítulo 4',
          description:
              'Aprende el movimiento en L del caballo, los saltos tácticos '
              'por encima de otras piezas y cómo dominar el centro.',
          symbol: ChapterSymbol.knight,
          alignment: PathAlignment.center,
          xp: 45,
          stepsTotal: 8,
          route: '/learning/initial-position',
        ),
        LearningChapter(
          id: 'cap-5-captura',
          title: 'Captura de piezas',
          subtitle: 'Capítulo 5 • Próximo reto',
          symbol: ChapterSymbol.capture,
          alignment: PathAlignment.right,
          xp: 50,
          stepsTotal: 6,
        ),
        LearningChapter(
          id: 'cap-6-jaque',
          title: 'Jaque y jaque mate',
          subtitle: 'Capítulo 6 • Desbloquea con Cap. 5',
          symbol: ChapterSymbol.checkmate,
          alignment: PathAlignment.left,
          xp: 60,
          stepsTotal: 6,
        ),
        LearningChapter(
          id: 'cap-7-estrategias',
          title: 'Estrategias básicas',
          subtitle: 'Capítulo 7 • 0%',
          symbol: ChapterSymbol.strategy,
          alignment: PathAlignment.right,
          xp: 60,
          stepsTotal: 6,
        ),
        LearningChapter(
          id: 'cap-8-puzzles',
          title: 'Puzzles y práctica',
          subtitle: 'Capítulo 8 • Evaluación Final Stockfish',
          symbol: ChapterSymbol.trophy,
          alignment: PathAlignment.center,
          isBoss: true,
          xp: 100,
          stepsTotal: 10,
        ),
      ],
    );
  }

  /// Deriva el estado de cada capítulo a partir del progreso del jugador.
  ///
  /// Regla de desbloqueo secuencial:
  /// - capítulos antes de `completedChapters` → completados
  /// - el capítulo en curso (`activeChapterIndex`) → en progreso
  /// - el siguiente → disponible
  /// - el resto → bloqueado
  List<ResolvedChapter> resolver(
    LearningUnit unidad,
    LearningProgress progreso, {
    LearningProgress? sobre,
  }) {
    final p = sobre ?? progreso;
    final efectivoActivo = p.activeChapterIndex.clamp(p.completedChapters, unidad.chapters.length);
    return List.generate(unidad.chapters.length, (i) {
      final capitulo = unidad.chapters[i];
      ChapterStatus estado;
      int pasos;
      if (i < p.completedChapters) {
        estado = ChapterStatus.completed;
        pasos = capitulo.stepsTotal;
      } else if (i == efectivoActivo) {
        estado = ChapterStatus.inProgress;
        pasos = p.activeChapterSteps;
      } else if (i == efectivoActivo + 1) {
        estado = ChapterStatus.available;
        pasos = 0;
      } else {
        estado = ChapterStatus.locked;
        pasos = 0;
      }
      return ResolvedChapter(chapter: capitulo, status: estado, stepsDone: pasos);
    });
  }

  /// Fracción del camino completada (capítulos completados / total). 0..1.
  double fraccionCompletada(LearningUnit unidad, LearningProgress progreso) {
    if (unidad.chapters.isEmpty) return 0;
    return progreso.completedChapters / unidad.chapters.length;
  }

  /// Lecciones que faltan para terminar el capítulo en curso.
  /// (Coincide con la métrica del mockup: "5 lecciones pendientes".)
  int leccionesPendientes(
    LearningUnit unidad,
    LearningProgress progreso, {
    LearningProgress? sobre,
  }) {
    final activo = capituloActivo(unidad, progreso, sobre: sobre);
    if (activo == null) return 0;
    return activo.chapter.stepsTotal - activo.stepsDone;
  }

  /// Capítulo en progreso, o `null` si el camino está completo.
  ResolvedChapter? capituloActivo(
    LearningUnit unidad,
    LearningProgress progreso, {
    LearningProgress? sobre,
  }) {
    final resuelto = resolver(unidad, progreso, sobre: sobre);
    for (final r in resuelto) {
      if (r.status == ChapterStatus.inProgress) return r;
    }
    return null;
  }

  /// Total de XP acumulable en la unidad (todos los capítulos).
  int xpTotal(LearningUnit unidad) =>
      unidad.chapters.fold<int>(0, (sum, c) => sum + c.xp);
}