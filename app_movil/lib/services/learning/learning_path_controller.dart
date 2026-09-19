import 'package:flutter/foundation.dart';

import '../../models/learning/learning_models.dart';
import 'learning_service.dart';

/// Estado del "Camino de Maestría" para la pantalla de aprendizaje.
///
/// Separa la lógica de negocio ([LearningService]) del estado de la sesión:
/// el progreso vive acá y se notifica a los widgets cuando cambia. En el
/// futuro el progreso puede venir de la API (el servicio ya está separado
/// para poder cambiarlo sin tocar la UI).
class LearningPathController extends ChangeNotifier {
  final LearningService _service;
  LearningProgress _progress;

  LearningPathController({
    LearningService? service,
    LearningProgress? progress,
  })  : _service = service ?? const LearningService(),
        _progress = progress ?? LearningProgress.inicial();

  LearningUnit get unidad => _service.unidadInicial();

  List<ResolvedChapter> get capitulos => _service.resolver(unidad, _progress);

  ResolvedChapter? get capituloActivo =>
      _service.capituloActivo(unidad, _progress);

  /// 0..1, fracción del camino completada.
  double get fraccionCompletada => _service.fraccionCompletada(unidad, _progress);

  /// Lecciones restantes del capítulo en curso.
  int get leccionesPendientes => _service.leccionesPendientes(unidad, _progress);

  int get xp => _progress.xp;
  int get racha => _progress.streakDays;
  int get nivel => _progress.nivel;
  String get rankLabel => _progress.rankLabel;
  int get capitulosCompletados => _progress.completedChapters;
  int get totalCapitulos => unidad.chapters.length;
  int get xpTotal => _service.xpTotal(unidad);

  /// Registra un paso completado dentro del capítulo en curso. Si se llega
  /// al último paso, el capítulo se marca como completado automáticamente.
  void completarPaso() {
    final activo = capituloActivo;
    if (activo == null) return;
    final siguiente = activo.stepsDone + 1;
    if (siguiente >= activo.chapter.stepsTotal) {
      _completarCapitulo(activo.chapter.id, xpGanada: activo.chapter.xp);
    } else {
      final pasos = activo.chapter.stepsTotal;
      final xpPorPaso = pasos > 0 ? activo.chapter.xp ~/ pasos : activo.chapter.xp;
      _progress = _progress.copyWith(
        activeChapterSteps: siguiente,
        xp: _progress.xp + xpPorPaso,
      );
      notifyListeners();
    }
  }

  /// Marca un capítulo como completado y avanza el activo al siguiente.
  void marcarCapituloCompletado(String chapterId, {int? xpGanada}) {
    _completarCapitulo(chapterId, xpGanada: xpGanada);
  }

  void _completarCapitulo(String chapterId, {int? xpGanada}) {
    final idx = unidad.chapters.indexWhere((c) => c.id == chapterId);
    if (idx < 0) return;
    if (idx >= _progress.completedChapters) {
      _progress = _progress.copyWith(
        completedChapters: idx + 1,
        activeChapterIndex: idx + 1,
        activeChapterSteps: 0,
        xp: _progress.xp + (xpGanada ?? unidad.chapters[idx].xp),
      );
      notifyListeners();
    }
  }
}