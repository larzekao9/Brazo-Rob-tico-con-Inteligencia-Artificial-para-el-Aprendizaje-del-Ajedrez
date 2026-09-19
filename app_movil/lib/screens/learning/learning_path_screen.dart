import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../models/learning/learning_models.dart';
import '../../services/learning/learning_path_controller.dart';
import '../../theme.dart';
import '../../widgets.dart';

/// Pantalla "Aprender / Camino de Maestría".
///
/// Composición de widgets reutilizables + datos del
/// [LearningPathController]. No contiene lógica de negocio: toda la
/// derivación de estados/progreso vive en `learning_service.dart`.
class LearningPathScreen extends StatelessWidget {
  static const String routeName = '/learning-path';

  const LearningPathScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => LearningPathController(),
      child: const _LearningPathView(),
    );
  }
}

class _LearningPathView extends StatelessWidget {
  const _LearningPathView();

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<LearningPathController>();
    final unidad = controller.unidad;

    return Scaffold(
      backgroundColor: AppColors.surface,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.spaceXl),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                LearningPathHeader(
                  title: 'Camino de Maestría',
                  subtitle: 'Aprender',
                  streakDays: controller.racha,
                  onBack: () => context.go('/home'),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.margin,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      LearningPathProgressCard(
                        nivel: controller.nivel,
                        rankLabel: controller.rankLabel,
                        xp: controller.xp,
                        completedChapters: controller.capitulosCompletados,
                        totalChapters: controller.totalCapitulos,
                        pendingLessons: controller.leccionesPendientes,
                        fraction: controller.fraccionCompletada,
                      ),
                      const SizedBox(height: AppSpacing.spaceLg),
                      LearningPathUnitBanner(unit: unidad),
                      const SizedBox(height: AppSpacing.spaceLg + 4),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.margin,
                  ),
                  child: LearningPath(
                    chapters: controller.capitulos,
                    onChapterTap: (r) => _abrirCapitulo(context, r),
                    onContinueLesson: (r) => _abrirCapitulo(context, r),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _abrirCapitulo(BuildContext context, ResolvedChapter resuelto) {
    final ruta = resuelto.chapter.route;
    if (ruta != null) {
      context.go(ruta);
      return;
    }
    final mensaje = resuelto.status == ChapterStatus.locked
        ? 'Completa el capítulo anterior para desbloquear este.'
        : 'Esta lección llega pronto.';
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(mensaje)),
    );
  }
}