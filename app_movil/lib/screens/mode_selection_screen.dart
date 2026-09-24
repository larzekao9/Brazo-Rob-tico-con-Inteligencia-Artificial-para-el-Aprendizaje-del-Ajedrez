import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../models.dart';
import '../services/chess_api.dart';

/// Nivel de Stockfish para la partida de diagnóstico — fijo, no lo elige el
/// jugador: la idea es medir cómo juega contra un rival constante, no dejarlo
/// autoseleccionar la dificultad.
const _nivelDiagnostico = 10;

/// Nivel bajo para test rápido (termina en pocas jugadas).
const _nivelTestRapido = 2;

/// Cuántas partidas cortas seguidas se juegan para calcular el nivel —
/// promediamos la precisión de todas en vez de fiarnos de una sola.
const _rondasDiagnostico = 3;

/// Una sola ronda para el test rápido.
const _rondasTestRapido = 1;

/// Pantalla "¿Qué quieres hacer ahora?" (diseño 03_seleccion_de_modo) —
/// llega acá tanto al saltar las tarjetas de aprendizaje como al terminarlas.
class ModeSelectionScreen extends StatefulWidget {
  const ModeSelectionScreen({super.key});

  @override
  State<ModeSelectionScreen> createState() => _ModeSelectionScreenState();
}

class _ModeSelectionScreenState extends State<ModeSelectionScreen> {
  bool _creandoDiagnostico = false;
  bool _creandoTestRapido = false;
  bool _creandoModeloIA = false;

  Future<void> _comenzarContraModelo() async {
    setState(() => _creandoModeloIA = true);
    try {
      final partida = await ChessApi.instancia.crearPartida(
        nivel: 20,
        tipoOponente: 'modelo',
      );
      if (!mounted) return;
      context.go('/game', extra: {
        'partidaId': partida.id,
        'opponent': OpponentType.model,
        'level': 20,
        'enableFeedback': true,
        'esDiagnostico': false,
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ChessApi.mensajeDeError(error))),
      );
    } finally {
      if (mounted) setState(() => _creandoModeloIA = false);
    }
  }

  Future<void> _comenzarDiagnostico() async {
    setState(() => _creandoDiagnostico = true);
    try {
      final partida = await ChessApi.instancia.crearPartida(
        nivel: _nivelDiagnostico,
        tipoOponente: 'motor',
      );
      if (!mounted) return;
      context.go('/game', extra: {
        'partidaId': partida.id,
        'opponent': OpponentType.stockfish,
        'level': _nivelDiagnostico,
        'enableFeedback': true,
        'esDiagnostico': true,
        'diagnosticoRonda': 1,
        'diagnosticoTotalRondas': _rondasDiagnostico,
        'diagnosticoPrecisiones': <double>[],
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ChessApi.mensajeDeError(error))),
      );
    } finally {
      if (mounted) setState(() => _creandoDiagnostico = false);
    }
  }

  Future<void> _comenzarTestRapido() async {
    setState(() => _creandoTestRapido = true);
    try {
      final partida = await ChessApi.instancia.crearPartida(
        nivel: _nivelTestRapido,
        tipoOponente: 'motor',
      );
      if (!mounted) return;
      context.go('/game', extra: {
        'partidaId': partida.id,
        'opponent': OpponentType.stockfish,
        'level': _nivelTestRapido,
        'enableFeedback': true,
        'esDiagnostico': true,
        'diagnosticoRonda': 1,
        'diagnosticoTotalRondas': _rondasTestRapido,
        'diagnosticoPrecisiones': <double>[],
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ChessApi.mensajeDeError(error))),
      );
    } finally {
      if (mounted) setState(() => _creandoTestRapido = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.margin),
          child: Column(
            children: [
              const SizedBox(height: AppSpacing.spaceLg),
              Text('♛',
                  style: AppTextStyles.displayLg
                      .copyWith(fontSize: 56, color: AppColors.primary)),
              const SizedBox(height: AppSpacing.spaceSm),
              RichText(
                text: TextSpan(
                  style: AppTextStyles.headlineLg,
                  children: [
                    TextSpan(
                        text: 'Chess',
                        style: TextStyle(color: AppColors.onSurface)),
                    TextSpan(
                        text: 'IA',
                        style: TextStyle(color: AppColors.tertiaryFixedDim)),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.spaceXl),
              Text(
                '¿Qué quieres hacer ahora?',
                style: AppTextStyles.headlineMd
                    .copyWith(color: AppColors.onSurface),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.spaceXs),
              Text(
                'Elige la opción que mejor se adapte a tu objetivo.',
                style: AppTextStyles.bodyMd
                    .copyWith(color: AppColors.onSurfaceVariant),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.spaceXl),
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      _ModeCard(
                        icon: Icons.psychology,
                        color: AppColors.primary,
                        title: 'Desafío IA: Red Neuronal v5',
                        description:
                            'Enfréntate a la IA de maestría FIDE propia (SE-ResNet-8). Juega de forma 100% autónoma con poda táctica y visión posicional.',
                        enabled: true,
                        badge: 'Maestría FIDE',
                        cargando: _creandoModeloIA,
                        onTap: _comenzarContraModelo,
                      ),
                      const SizedBox(height: AppSpacing.spaceLg),
                      _ModeCard(
                        icon: Icons.school_outlined,
                        color: AppColors.primary,
                        title: 'Modo de enseñanza',
                        description:
                            'Aprende paso a paso con la guía de la IA. Lecciones, ejercicios y práctica interactiva.',
                        enabled: false,
                        badge: 'Próximamente',
                        onTap: () {},
                      ),
                      const SizedBox(height: AppSpacing.spaceLg),
                      _ModeCard(
                        icon: Icons.bar_chart_rounded,
                        color: AppColors.tertiary,
                        title: 'Mide tu nivel (3 partidas)',
                        description:
                            'Jugá 3 partidas reales con Stockfish nivel 10. Promediamos tu precisión para '
                            'clasificarte como principiante, intermedio o avanzado.',
                        enabled: true,
                        cargando: _creandoDiagnostico,
                        onTap: _comenzarDiagnostico,
                      ),
                      const SizedBox(height: AppSpacing.spaceLg),
                      _ModeCard(
                        icon: Icons.flash_on,
                        color: AppColors.secondary,
                        title: 'Test rápido (1 partida)',
                        description:
                            'Una sola partida contra Stockfish nivel 2. Termina en segundos y te da tu '
                            'nivel estimado al instante.',
                        enabled: true,
                        cargando: _creandoTestRapido,
                        onTap: _comenzarTestRapido,
                      ),
                    ],
                  ),
                ),
              ),
              TextButton.icon(
                onPressed: () => context.go('/learning/board-basics'),
                icon: const Icon(Icons.chevron_left, size: 18),
                label: const Text('Volver'),
                style: TextButton.styleFrom(
                    foregroundColor: AppColors.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ModeCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String description;
  final bool enabled;
  final bool cargando;
  final String? badge;
  final VoidCallback onTap;

  const _ModeCard({
    required this.icon,
    required this.color,
    required this.title,
    required this.description,
    required this.enabled,
    this.cargando = false,
    this.badge,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      decoration: BoxDecoration(
        color:
            enabled ? color.withOpacity(0.08) : AppColors.surfaceContainerLow,
        borderRadius: AppRadius.radiusXl,
        border: Border.all(
            color: enabled ? color.withOpacity(0.4) : AppColors.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: enabled
                      ? color.withOpacity(0.15)
                      : AppColors.outlineVariant,
                  borderRadius: AppRadius.radiusMd,
                ),
                child: Icon(icon,
                    color: enabled ? color : AppColors.onSurfaceVariant),
              ),
              const Spacer(),
              if (badge != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.spaceSm,
                      vertical: AppSpacing.spaceXs),
                  decoration: BoxDecoration(
                    color: AppColors.tertiaryContainer,
                    borderRadius: AppRadius.radiusFull,
                  ),
                  child: Text(badge!,
                      style: AppTextStyles.labelSm
                          .copyWith(color: AppColors.onTertiaryContainer)),
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceMd),
          Text(
            title,
            style: AppTextStyles.headlineSm.copyWith(
              color: enabled ? AppColors.onSurface : AppColors.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: AppSpacing.spaceXs),
          Text(
            description,
            style: AppTextStyles.bodySm
                .copyWith(color: AppColors.onSurfaceVariant),
          ),
          const SizedBox(height: AppSpacing.spaceMd),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: enabled && !cargando ? onTap : null,
              icon: cargando
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: AppColors.onPrimary),
                    )
                  : const Icon(Icons.chevron_right, size: 18),
              label: Text(cargando ? 'Creando partida…' : 'Comenzar'),
              style: FilledButton.styleFrom(
                backgroundColor: enabled ? color : AppColors.outlineVariant,
                foregroundColor:
                    enabled ? AppColors.onPrimary : AppColors.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
