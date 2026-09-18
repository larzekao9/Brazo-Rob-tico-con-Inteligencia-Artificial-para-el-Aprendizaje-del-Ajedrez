import 'dart:ui';
import 'package:flutter/material.dart';
import '../theme.dart';

class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final double? width;
  final double? height;
  final BorderRadius? borderRadius;
  final List<BoxShadow>? shadows;
  final Color? surfaceColor;
  final Color? borderColor;
  final Color? highlightColor;
  final VoidCallback? onTap;
  final bool enableBlur;

  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.width,
    this.height,
    this.borderRadius,
    this.shadows,
    this.surfaceColor,
    this.borderColor,
    this.highlightColor,
    this.onTap,
    this.enableBlur = true,
  });

  @override
  Widget build(BuildContext context) {
    final card = Container(
      width: width,
      height: height,
      margin: margin,
      padding: padding ?? AppSpacing.cardPadding,
      decoration: BoxDecoration(
        color: surfaceColor ?? AppColors.surfaceGlass,
        borderRadius: borderRadius ?? AppRadius.radiusXl,
        border: Border.all(
          color: borderColor ?? AppColors.surfaceGlassBorder,
          width: 1,
        ),
        boxShadow: shadows ?? AppShadows.glassMorphic(),
      ),
      child: enableBlur
          ? ClipRRect(
              borderRadius: borderRadius ?? AppRadius.radiusXl,
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
                child: child,
              ),
            )
          : child,
    );

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: borderRadius ?? AppRadius.radiusXl,
        child: card,
      );
    }

    return card;
  }
}

class GlassHUD extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final double? width;
  final double? height;
  final BorderRadius? borderRadius;

  const GlassHUD({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.width,
    this.height,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      margin: margin,
      padding: padding ?? AppSpacing.cardPadding,
      decoration: BoxDecoration(
        color: AppColors.surfaceGlass,
        borderRadius: borderRadius ?? AppRadius.radiusXl,
        border: Border.all(
          color: AppColors.surfaceGlassBorder,
          width: 1,
        ),
        boxShadow: [
          ...AppShadows.glassMorphic(),
          BoxShadow(
            color: AppColors.surfaceGlassHighlight,
            offset: const Offset(0, -1),
            blurRadius: 0,
            spreadRadius: 0,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: borderRadius ?? AppRadius.radiusXl,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
          child: child,
        ),
      ),
    );
  }
}

class TacticalCard extends StatelessWidget {
  final Widget child;
  final String? title;
  final Widget? titleTrailing;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;

  const TacticalCard({
    super.key,
    required this.child,
    this.title,
    this.titleTrailing,
    this.padding,
    this.margin,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final card = Container(
      margin: margin,
      padding: padding ?? AppSpacing.cardPadding,
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerLowest,
        borderRadius: AppRadius.radiusLg,
        border: Border.all(
          color: AppColors.outlineVariant,
          width: 1,
        ),
        boxShadow: AppShadows.level1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (title != null) ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    title!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTextStyles.headlineSm.copyWith(
                      color: AppColors.onSurface,
                    ),
                  ),
                ),
                if (titleTrailing != null) titleTrailing!,
              ],
            ),
            const SizedBox(height: AppSpacing.spaceMd),
          ],
          child,
        ],
      ),
    );

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: AppRadius.radiusLg,
        child: card,
      );
    }

    return card;
  }
}

class TelemetryPill extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;
  final IconData? icon;

  const TelemetryPill({
    super.key,
    required this.label,
    required this.value,
    this.valueColor,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.spaceMd,
        vertical: AppSpacing.spaceSm,
      ),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: AppRadius.radiusFull,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: AppColors.onSurfaceVariant),
            const SizedBox(width: AppSpacing.spaceXs),
          ],
          Text(
            label,
            style: AppTextStyles.labelSm.copyWith(
              color: AppColors.onSurfaceVariant,
            ),
          ),
          const SizedBox(width: AppSpacing.spaceSm),
          Text(
            value,
            style: AppTextStyles.telemetrySm.copyWith(
              color: valueColor ?? AppColors.onSurface,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}