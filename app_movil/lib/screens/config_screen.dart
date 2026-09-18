import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../widgets.dart';
import '../models.dart';
import '../services/chess_api.dart';

class ConfigScreen extends StatefulWidget {
  final int diagnosticLevel;

  const ConfigScreen({super.key, required this.diagnosticLevel});

  @override
  State<ConfigScreen> createState() => _ConfigScreenState();
}

class _ConfigScreenState extends State<ConfigScreen> {
  late OpponentType _selectedOpponent;
  late int _selectedLevel;
  bool _enableFeedback = true;

  @override
  void initState() {
    super.initState();
    _selectedOpponent = OpponentType.stockfish;
    _selectedLevel = widget.diagnosticLevel.clamp(1, 20);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _TopBar(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(AppSpacing.margin),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _OpponentSelector(
                      selected: _selectedOpponent,
                      onChanged: (type) => setState(() => _selectedOpponent = type),
                    ),
                    const SizedBox(height: AppSpacing.spaceLg),
                    _LevelSlider(
                      level: _selectedLevel,
                      onChanged: (level) => setState(() => _selectedLevel = level),
                    ),
                    const SizedBox(height: AppSpacing.spaceLg),
                    _FeedbackToggle(
                      enabled: _enableFeedback,
                      onChanged: (val) => setState(() => _enableFeedback = val),
                    ),
                    const SizedBox(height: AppSpacing.spaceXl),
                    _StartButton(
                      opponent: _selectedOpponent,
                      level: _selectedLevel,
                      enableFeedback: _enableFeedback,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.chevron_left, color: AppColors.onSurface),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Configurar Partida',
                  style: AppTextStyles.headlineSm.copyWith(
                    color: AppColors.onSurface,
                  ),
                ),
                Text(
                  'Elige oponente, nivel y opciones',
                  style: AppTextStyles.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
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

class _OpponentSelector extends StatelessWidget {
  final OpponentType selected;
  final ValueChanged<OpponentType> onChanged;

  const _OpponentSelector({
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Oponente',
            style: AppTextStyles.headlineSm.copyWith(color: AppColors.onSurface),
          ),
          const SizedBox(height: AppSpacing.spaceMd),
          _OpponentOption(
            type: OpponentType.stockfish,
            title: 'Motor Stockfish',
            subtitle: 'Motor clásico, niveles 1-20',
            icon: Icons.memory_outlined,
            iconColor: AppColors.primary,
            isSelected: selected == OpponentType.stockfish,
            enabled: true,
            onTap: () => onChanged(OpponentType.stockfish),
          ),
          const SizedBox(height: AppSpacing.spaceMd),
          _OpponentOption(
            type: OpponentType.model,
            title: 'Modelo IA (Neural)',
            subtitle: 'Modelo propio entrenado, estilo humano',
            icon: Icons.psychology_outlined,
            iconColor: AppColors.secondary,
            isSelected: selected == OpponentType.model,
            enabled: true, // HU4: ya hay checkpoint entrenado y estrategia conectada en el backend
            onTap: () => onChanged(OpponentType.model),
          ),
        ],
      ),
    );
  }
}

class _OpponentOption extends StatelessWidget {
  final OpponentType type;
  final String title;
  final String subtitle;
  final IconData icon;
  final Color iconColor;
  final bool isSelected;
  final bool enabled;
  final VoidCallback onTap;

  const _OpponentOption({
    required this.type,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.iconColor,
    required this.isSelected,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: AppRadius.radiusLg,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(AppSpacing.spaceMd),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primaryContainer
              : (enabled ? AppColors.surfaceContainerLowest : AppColors.surfaceContainerLow),
          borderRadius: AppRadius.radiusLg,
          border: Border.all(
            color: isSelected
                ? AppColors.primary
                : (enabled ? AppColors.outlineVariant : AppColors.outlineVariant.withOpacity(0.5)),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: isSelected ? AppShadows.level2 : AppShadows.level1,
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: isSelected
                    ? AppColors.primary
                    : (enabled ? iconColor.withOpacity(0.15) : AppColors.outlineVariant),
                borderRadius: AppRadius.radiusMd,
              ),
              child: Icon(
                icon,
                color: isSelected
                    ? AppColors.onPrimary
                    : (enabled ? iconColor : AppColors.onSurfaceVariant),
                size: 22,
              ),
            ),
            const SizedBox(width: AppSpacing.spaceMd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: AppTextStyles.bodyLg.copyWith(
                      color: enabled
                          ? (isSelected ? AppColors.primary : AppColors.onSurface)
                          : AppColors.onSurfaceVariant,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: AppTextStyles.bodySm.copyWith(
                      color: enabled
                          ? AppColors.onSurfaceVariant
                          : AppColors.onSurfaceVariant.withOpacity(0.6),
                    ),
                  ),
                ],
              ),
            ),
            if (!enabled)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.spaceSm,
                  vertical: AppSpacing.spaceXs,
                ),
                decoration: BoxDecoration(
                  color: AppColors.tertiaryContainer,
                  borderRadius: AppRadius.radiusFull,
                ),
                child: Text(
                  'Próximamente',
                  style: AppTextStyles.labelSm.copyWith(
                    color: AppColors.onTertiaryContainer,
                  ),
                ),
              ),
            if (enabled && isSelected)
              Icon(
                Icons.check_circle,
                color: AppColors.primary,
                size: 24,
              ),
          ],
        ),
      ),
    );
  }
}

class _LevelSlider extends StatelessWidget {
  final int level;
  final ValueChanged<int> onChanged;

  const _LevelSlider({
    required this.level,
    required this.onChanged,
  });

  String _levelLabel(int l) {
    if (l <= 5) return 'Principiante';
    if (l <= 10) return 'Club';
    if (l <= 15) return 'Experto';
    if (l <= 18) return 'Maestro';
    return 'Gran Maestro';
  }

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Nivel de Dificultad',
                style: AppTextStyles.headlineSm.copyWith(color: AppColors.onSurface),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.spaceMd,
                  vertical: AppSpacing.spaceXs,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primaryContainer,
                  borderRadius: AppRadius.radiusFull,
                ),
                child: Text(
                  'Nivel $level • ${_levelLabel(level)}',
                  style: AppTextStyles.labelMd.copyWith(color: AppColors.primary),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.spaceLg),
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              activeTrackColor: AppColors.primary,
              inactiveTrackColor: AppColors.primaryContainer,
              thumbColor: AppColors.primary,
              overlayColor: AppColors.primary.withOpacity(0.12),
              valueIndicatorColor: AppColors.primary,
              valueIndicatorTextStyle: AppTextStyles.labelSm.copyWith(
                color: AppColors.onPrimary,
              ),
              trackHeight: 6,
              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 12),
              overlayShape: const RoundSliderOverlayShape(overlayRadius: 24),
            ),
            child: Slider(
              value: level.toDouble(),
              min: 1,
              max: 20,
              divisions: 19,
              label: '$level',
              onChanged: (v) => onChanged(v.round()),
            ),
          ),
          const SizedBox(height: AppSpacing.spaceMd),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Fácil',
                style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
              ),
              Text(
                'Difícil',
                style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _FeedbackToggle extends StatelessWidget {
  final bool enabled;
  final ValueChanged<bool> onChanged;

  const _FeedbackToggle({
    required this.enabled,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(AppSpacing.spaceLg),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColors.secondary.withOpacity(0.15),
              borderRadius: AppRadius.radiusMd,
            ),
            child: Icon(
              Icons.lightbulb_outline,
              color: AppColors.secondary,
              size: 22,
            ),
          ),
          const SizedBox(width: AppSpacing.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Retroalimentación en vivo',
                  style: AppTextStyles.bodyLg.copyWith(
                    color: AppColors.onSurface,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Muestra análisis, evaluación y sugerencias durante la partida',
                  style: AppTextStyles.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: enabled,
            onChanged: onChanged,
            activeColor: AppColors.primary,
            activeTrackColor: AppColors.primaryContainer,
            inactiveThumbColor: AppColors.outline,
            inactiveTrackColor: AppColors.outlineVariant,
          ),
        ],
      ),
    );
  }
}

class _StartButton extends StatefulWidget {
  final OpponentType opponent;
  final int level;
  final bool enableFeedback;

  const _StartButton({
    required this.opponent,
    required this.level,
    required this.enableFeedback,
  });

  @override
  State<_StartButton> createState() => _StartButtonState();
}

class _StartButtonState extends State<_StartButton> {
  bool _creando = false;

  Future<void> _comenzarPartida() async {
    setState(() => _creando = true);
    try {
      final tipoOponente = widget.opponent == OpponentType.model ? 'modelo' : 'motor';
      final partida = await ChessApi.instancia.crearPartida(
        nivel: widget.level,
        tipoOponente: tipoOponente,
      );
      if (!mounted) return;
      context.go('/game', extra: {
        'partidaId': partida.id,
        'opponent': widget.opponent,
        'level': widget.level,
        'enableFeedback': widget.enableFeedback,
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ChessApi.mensajeDeError(error))),
      );
    } finally {
      if (mounted) setState(() => _creando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: _creando ? null : _comenzarPartida,
      style: FilledButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.spaceLg),
      ),
      child: _creando
          ? const SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2.5, color: AppColors.onPrimary),
            )
          : Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.play_arrow, size: 24),
                const SizedBox(width: AppSpacing.spaceMd),
                Text(
                  'Comenzar Partida',
                  style: AppTextStyles.labelMd.copyWith(fontSize: 18),
                ),
              ],
            ),
    );
  }
}