import 'package:flutter/material.dart';
import '../theme.dart';

class ChessClock extends StatelessWidget {
  final Duration whiteTime;
  final Duration blackTime;
  final bool isWhiteTurn;
  final bool isLowTimeWhite;
  final bool isLowTimeBlack;
  final VoidCallback? onTapWhite;
  final VoidCallback? onTapBlack;

  const ChessClock({
    super.key,
    required this.whiteTime,
    required this.blackTime,
    required this.isWhiteTurn,
    this.isLowTimeWhite = false,
    this.isLowTimeBlack = false,
    this.onTapWhite,
    this.onTapBlack,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _ClockPill(
            time: blackTime,
            isActive: !isWhiteTurn,
            isLowTime: isLowTimeBlack,
            onTap: onTapBlack,
          ),
        ),
        const SizedBox(width: AppSpacing.spaceMd),
        Expanded(
          child: _ClockPill(
            time: whiteTime,
            isActive: isWhiteTurn,
            isLowTime: isLowTimeWhite,
            onTap: onTapWhite,
          ),
        ),
      ],
    );
  }
}

class _ClockPill extends StatelessWidget {
  final Duration time;
  final bool isActive;
  final bool isLowTime;
  final VoidCallback? onTap;

  const _ClockPill({
    required this.time,
    required this.isActive,
    required this.isLowTime,
    this.onTap,
  });

  String _formatTime(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    final centis = (d.inMilliseconds.remainder(1000) ~/ 10).toString().padLeft(2, '0');
    return '$minutes:$seconds.$centis';
  }

  @override
  Widget build(BuildContext context) {
    final bgColor = isLowTime
        ? AppColors.clockLowTimeBg
        : AppColors.surfaceContainerLowest;
    final textColor = isLowTime
        ? AppColors.clockLowTimeText
        : AppColors.onSurface;
    final accentColor = isActive ? AppColors.clockActive : Colors.transparent;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.spaceLg,
          vertical: AppSpacing.spaceMd,
        ),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: AppRadius.radiusFull,
          border: Border.all(
            color: isActive
                ? AppColors.clockActive.withOpacity(0.5)
                : AppColors.outlineVariant,
            width: isActive ? 2 : 1,
          ),
          boxShadow: isActive ? AppShadows.level2 : AppShadows.level1,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isActive) ...[
              _PulseDot(color: accentColor),
              const SizedBox(width: AppSpacing.spaceSm),
            ],
            Text(
              _formatTime(time),
              style: AppTextStyles.telemetryLg.copyWith(
                color: textColor,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PulseDot extends StatefulWidget {
  final Color color;

  const _PulseDot({required this.color});

  @override
  State<_PulseDot> createState() => _PulseDotState();
}

class _PulseDotState extends State<_PulseDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, __) => Opacity(
        opacity: 0.4 + 0.6 * _controller.value,
        child: Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: widget.color,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: widget.color.withOpacity(0.5),
                blurRadius: 8,
                spreadRadius: 2,
              ),
            ],
          ),
        ),
      ),
    );
  }
}