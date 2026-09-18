import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_text_styles.dart';
import 'app_spacing.dart';
import 'app_shadows.dart';

class AppTheme {
  AppTheme._();

  static ThemeData get lightTheme {
    final ColorScheme colorScheme = ColorScheme(
      brightness: Brightness.light,
      primary: AppColors.primary,
      onPrimary: AppColors.onPrimary,
      primaryContainer: AppColors.primaryContainer,
      onPrimaryContainer: AppColors.onPrimaryContainer,
      secondary: AppColors.secondary,
      onSecondary: AppColors.onSecondary,
      secondaryContainer: AppColors.secondaryContainer,
      onSecondaryContainer: AppColors.onSecondaryContainer,
      tertiary: AppColors.tertiary,
      onTertiary: AppColors.onTertiary,
      tertiaryContainer: AppColors.tertiaryContainer,
      onTertiaryContainer: AppColors.onTertiaryContainer,
      error: AppColors.error,
      onError: AppColors.onError,
      errorContainer: AppColors.errorContainer,
      onErrorContainer: AppColors.onErrorContainer,
      surface: AppColors.surface,
      onSurface: AppColors.onSurface,
      surfaceContainerHighest: AppColors.surfaceContainerHighest,
      surfaceContainerHigh: AppColors.surfaceContainerHigh,
      surfaceContainer: AppColors.surfaceContainer,
      surfaceContainerLow: AppColors.surfaceContainerLow,
      surfaceContainerLowest: AppColors.surfaceContainerLowest,
      surfaceVariant: AppColors.surfaceVariant,
      onSurfaceVariant: AppColors.onSurfaceVariant,
      outline: AppColors.outline,
      outlineVariant: AppColors.outlineVariant,
      shadow: Colors.black,
      scrim: Colors.black,
      inverseSurface: AppColors.inverseSurface,
      onInverseSurface: AppColors.inverseOnSurface,
      inversePrimary: AppColors.inversePrimary,
      surfaceTint: AppColors.surfaceTint,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.background,
      canvasColor: AppColors.surface,
      cardColor: AppColors.surfaceContainerLowest,
      dividerColor: AppColors.outlineVariant,
      splashColor: AppColors.primary.withOpacity(0.12),
      highlightColor: AppColors.primary.withOpacity(0.08),
      hoverColor: AppColors.primary.withOpacity(0.06),
      focusColor: AppColors.primary.withOpacity(0.12),

      textTheme: AppTextStyles.textTheme.apply(
        bodyColor: AppColors.onSurface,
        displayColor: AppColors.onSurface,
      ),

      primaryTextTheme: AppTextStyles.textTheme.apply(
        bodyColor: AppColors.onPrimary,
        displayColor: AppColors.onPrimary,
      ),

      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.surfaceContainerLowest,
        foregroundColor: AppColors.onSurface,
        elevation: 0,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        centerTitle: true,
        titleTextStyle: AppTextStyles.headlineSm.copyWith(
          color: AppColors.onSurface,
        ),
        toolbarHeight: 56,
        shape: const Border(
          bottom: BorderSide(color: AppColors.outlineVariant, width: 1),
        ),
      ),

      cardTheme: CardThemeData(
        color: AppColors.surfaceContainerLowest,
        elevation: 0,
        shadowColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusLg,
          side: const BorderSide(color: AppColors.outlineVariant, width: 1),
        ),
        margin: EdgeInsets.zero,
        clipBehavior: Clip.antiAlias,
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.onPrimary,
          elevation: 0,
          shadowColor: Colors.transparent,
          surfaceTintColor: Colors.transparent,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.spaceLg,
            vertical: AppSpacing.spaceMd,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: AppRadius.radiusBase,
          ),
          textStyle: AppTextStyles.labelMd.copyWith(
            color: AppColors.onPrimary,
          ),
          minimumSize: const Size(double.infinity, 48),
        ),
      ),

      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.onPrimary,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.spaceLg,
            vertical: AppSpacing.spaceMd,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: AppRadius.radiusBase,
          ),
          textStyle: AppTextStyles.labelMd,
          minimumSize: const Size(double.infinity, 48),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          side: const BorderSide(
            color: AppColors.primary,
            width: 1.5,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.spaceLg,
            vertical: AppSpacing.spaceMd,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: AppRadius.radiusBase,
          ),
          textStyle: AppTextStyles.labelMd.copyWith(
            color: AppColors.primary,
          ),
          minimumSize: const Size(double.infinity, 48),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.secondary,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.spaceMd,
            vertical: AppSpacing.spaceSm,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: AppRadius.radiusBase,
          ),
          textStyle: AppTextStyles.labelMd.copyWith(
            color: AppColors.secondary,
          ),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceContainerLowest,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.spaceLg,
          vertical: AppSpacing.spaceMd,
        ),
        border: OutlineInputBorder(
          borderRadius: AppRadius.radiusBase,
          borderSide: const BorderSide(
            color: AppColors.outlineVariant,
            width: 1,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: AppRadius.radiusBase,
          borderSide: const BorderSide(
            color: AppColors.outlineVariant,
            width: 1,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: AppRadius.radiusBase,
          borderSide: const BorderSide(
            color: AppColors.primary,
            width: 2,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: AppRadius.radiusBase,
          borderSide: const BorderSide(
            color: AppColors.error,
            width: 1,
          ),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: AppRadius.radiusBase,
          borderSide: const BorderSide(
            color: AppColors.error,
            width: 2,
          ),
        ),
        disabledBorder: OutlineInputBorder(
          borderRadius: AppRadius.radiusBase,
          borderSide: const BorderSide(
            color: AppColors.outlineVariant,
            width: 1,
          ),
        ),
        labelStyle: AppTextStyles.bodyMd.copyWith(
          color: AppColors.onSurfaceVariant,
        ),
        hintStyle: AppTextStyles.bodyMd.copyWith(
          color: AppColors.onSurfaceVariant.withOpacity(0.6),
        ),
        errorStyle: AppTextStyles.bodySm.copyWith(
          color: AppColors.error,
        ),
        floatingLabelStyle: AppTextStyles.bodySm.copyWith(
          color: AppColors.primary,
        ),
        prefixIconColor: AppColors.onSurfaceVariant,
        suffixIconColor: AppColors.onSurfaceVariant,
      ),

      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppColors.primary;
          }
          return AppColors.surfaceContainerLowest;
        }),
        checkColor: WidgetStateProperty.all(AppColors.onPrimary),
        side: const BorderSide(
          color: AppColors.outline,
          width: 1.5,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusSm,
        ),
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        visualDensity: VisualDensity.compact,
      ),

      radioTheme: RadioThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppColors.primary;
          }
          return AppColors.onSurfaceVariant;
        }),
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        visualDensity: VisualDensity.compact,
      ),

      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppColors.primary;
          }
          return AppColors.outline;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppColors.primary.withOpacity(0.4);
          }
          return AppColors.outlineVariant;
        }),
        trackOutlineColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppColors.primary;
          }
          return AppColors.outline;
        }),
      ),

      sliderTheme: SliderThemeData(
        activeTrackColor: AppColors.primary,
        inactiveTrackColor: AppColors.primaryContainer,
        thumbColor: AppColors.primary,
        overlayColor: AppColors.primary.withOpacity(0.12),
        valueIndicatorColor: AppColors.primary,
        valueIndicatorTextStyle: AppTextStyles.labelSm.copyWith(
          color: AppColors.onPrimary,
        ),
        trackHeight: 4,
        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 10),
        overlayShape: const RoundSliderOverlayShape(overlayRadius: 20),
      ),

      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: AppColors.primary,
        linearTrackColor: AppColors.primaryContainer,
        circularTrackColor: AppColors.primaryContainer,
      ),

      chipTheme: ChipThemeData(
        backgroundColor: AppColors.surfaceContainerLow,
        disabledColor: AppColors.surfaceContainerLow.withOpacity(0.5),
        selectedColor: AppColors.primaryContainer,
        secondarySelectedColor: AppColors.primaryContainer,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.spaceMd,
          vertical: AppSpacing.spaceXs,
        ),
        labelStyle: AppTextStyles.labelMd.copyWith(
          color: AppColors.onSurface,
        ),
        secondaryLabelStyle: AppTextStyles.labelMd.copyWith(
          color: AppColors.onPrimaryContainer,
        ),
        brightness: Brightness.light,
        elevation: 0,
        shadowColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusFull,
          side: const BorderSide(
            color: AppColors.outlineVariant,
            width: 1,
          ),
        ),
      ),

      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: AppColors.surfaceContainerLowest,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadius.xl),
          ),
        ),
        clipBehavior: Clip.antiAlias,
        constraints: const BoxConstraints(
          minWidth: double.infinity,
        ),
      ),

      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.surfaceContainerLowest,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusXl,
          side: const BorderSide(
            color: AppColors.outlineVariant,
            width: 1,
          ),
        ),
        titleTextStyle: AppTextStyles.headlineSm.copyWith(
          color: AppColors.onSurface,
        ),
        contentTextStyle: AppTextStyles.bodyMd.copyWith(
          color: AppColors.onSurface,
        ),
      ),

      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.inverseSurface,
        contentTextStyle: AppTextStyles.bodyMd.copyWith(
          color: AppColors.inverseOnSurface,
        ),
        actionTextColor: AppColors.inversePrimary,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusLg,
        ),
        behavior: SnackBarBehavior.floating,
        elevation: 0,
      ),

      tabBarTheme: TabBarThemeData(
        labelColor: AppColors.primary,
        unselectedLabelColor: AppColors.onSurfaceVariant,
        indicatorColor: AppColors.primary,
        indicatorSize: TabBarIndicatorSize.label,
        labelStyle: AppTextStyles.labelMd,
        unselectedLabelStyle: AppTextStyles.labelMd,
        dividerColor: Colors.transparent,
        overlayColor: WidgetStateProperty.all(
          AppColors.primary.withOpacity(0.08),
        ),
      ),

      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.surfaceContainerLowest,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        indicatorColor: AppColors.primaryContainer,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppTextStyles.labelSm.copyWith(color: AppColors.primary);
          }
          return AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant);
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return IconThemeData(color: AppColors.primary, size: 24);
          }
          return IconThemeData(color: AppColors.onSurfaceVariant, size: 24);
        }),
        height: 72,
      ),

      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.onPrimary,
        elevation: 4,
        focusElevation: 6,
        hoverElevation: 6,
        highlightElevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusLg,
        ),
        extendedPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.spaceLg,
          vertical: AppSpacing.spaceMd,
        ),
        extendedTextStyle: AppTextStyles.labelMd.copyWith(
          color: AppColors.onPrimary,
        ),
      ),

      dividerTheme: DividerThemeData(
        color: AppColors.outlineVariant,
        thickness: 1,
        space: AppSpacing.spaceLg,
      ),

      listTileTheme: ListTileThemeData(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.spaceLg,
          vertical: AppSpacing.spaceXs,
        ),
        titleTextStyle: AppTextStyles.bodyLg.copyWith(
          color: AppColors.onSurface,
        ),
        subtitleTextStyle: AppTextStyles.bodySm.copyWith(
          color: AppColors.onSurfaceVariant,
        ),
        leadingAndTrailingTextStyle: AppTextStyles.bodySm.copyWith(
          color: AppColors.onSurfaceVariant,
        ),
        iconColor: AppColors.onSurfaceVariant,
        tileColor: Colors.transparent,
        selectedTileColor: AppColors.primaryContainer,
        selectedColor: AppColors.primary,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusMd,
        ),
      ),

      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: AppColors.inverseSurface,
          borderRadius: AppRadius.radiusBase,
        ),
        textStyle: AppTextStyles.bodySm.copyWith(
          color: AppColors.inverseOnSurface,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.spaceMd,
          vertical: AppSpacing.spaceSm,
        ),
        preferBelow: true,
        verticalOffset: 8,
      ),

      menuTheme: MenuThemeData(
        style: MenuStyle(
          backgroundColor: WidgetStateProperty.all(AppColors.surfaceContainerLowest),
          surfaceTintColor: WidgetStateProperty.all(Colors.transparent),
          elevation: WidgetStateProperty.all(0),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
              borderRadius: AppRadius.radiusMd,
              side: const BorderSide(
                color: AppColors.outlineVariant,
                width: 1,
              ),
            ),
          ),
        ),
      ),

      popupMenuTheme: PopupMenuThemeData(
        color: AppColors.surfaceContainerLowest,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusMd,
          side: const BorderSide(
            color: AppColors.outlineVariant,
            width: 1,
          ),
        ),
        textStyle: AppTextStyles.bodyMd.copyWith(
          color: AppColors.onSurface,
        ),
      ),

      timePickerTheme: TimePickerThemeData(
        backgroundColor: AppColors.surfaceContainerLowest,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusXl,
        ),
        hourMinuteTextStyle: AppTextStyles.telemetryLg.copyWith(
          color: AppColors.onSurface,
        ),
        dayPeriodTextStyle: AppTextStyles.labelMd.copyWith(
          color: AppColors.onSurfaceVariant,
        ),
        dialHandColor: AppColors.primary,
        dialBackgroundColor: AppColors.primaryContainer,
        entryModeIconColor: AppColors.primary,
      ),

      datePickerTheme: DatePickerThemeData(
        backgroundColor: AppColors.surfaceContainerLowest,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.radiusXl,
        ),
        headerBackgroundColor: AppColors.primary,
        headerForegroundColor: AppColors.onPrimary,
        dayStyle: AppTextStyles.bodyMd.copyWith(
          color: AppColors.onSurface,
        ),
        todayBackgroundColor: WidgetStateProperty.all(AppColors.primaryContainer),
        todayForegroundColor: WidgetStateProperty.all(AppColors.primary),
        rangePickerBackgroundColor: AppColors.surfaceContainerLowest,
        rangePickerHeaderBackgroundColor: AppColors.primary,
        rangePickerHeaderForegroundColor: AppColors.onPrimary,
      ),

      extensions: <ThemeExtension<dynamic>>[
        ChessThemeExtension(),
        _GlassMorphismExtension(),
      ],
    );
  }
}

class ChessThemeExtension extends ThemeExtension<ChessThemeExtension> {
  final Color whiteSquare = AppColors.chessWhiteSquare;
  final Color blackSquare = AppColors.chessBlackSquare;
  final Color highlight = AppColors.chessHighlight;
  final Color lastMove = AppColors.chessLastMove;
  final Color check = AppColors.chessCheck;
  final Color moveBrilliant = AppColors.moveBrilliant;
  final Color moveBest = AppColors.moveBest;
  final Color moveMistake = AppColors.moveMistake;
  final Color moveBlunder = AppColors.moveBlunder;

  @override
  ChessThemeExtension copyWith({
    Color? whiteSquare,
    Color? blackSquare,
    Color? highlight,
    Color? lastMove,
    Color? check,
    Color? moveBrilliant,
    Color? moveBest,
    Color? moveMistake,
    Color? moveBlunder,
  }) {
    return ChessThemeExtension();
  }

  @override
  ChessThemeExtension lerp(ThemeExtension<ChessThemeExtension>? other, double t) {
    return this;
  }
}

class _GlassMorphismExtension extends ThemeExtension<_GlassMorphismExtension> {
  final Color surface = AppColors.surfaceGlass;
  final Color border = AppColors.surfaceGlassBorder;
  final Color highlight = AppColors.surfaceGlassHighlight;
  final List<BoxShadow> shadows = AppShadows.glassMorphic();

  @override
  _GlassMorphismExtension copyWith({
    Color? surface,
    Color? border,
    Color? highlight,
    List<BoxShadow>? shadows,
  }) {
    return _GlassMorphismExtension();
  }

  @override
  _GlassMorphismExtension lerp(ThemeExtension<_GlassMorphismExtension>? other, double t) {
    return this;
  }
}