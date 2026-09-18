import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Usa `google_fonts` (ya declarado en pubspec.yaml) en vez de archivos .ttf
/// locales — evita depender de que alguien descargue manualmente Space
/// Grotesk / Plus Jakarta Sans / JetBrains Mono a assets/fonts/.
class AppTextStyles {
  AppTextStyles._();

  static TextStyle get displayLg => GoogleFonts.spaceGrotesk(
        fontSize: 36,
        fontWeight: FontWeight.w700,
        height: 44 / 36,
        letterSpacing: -0.03,
      );

  static TextStyle get displayLgMobile => GoogleFonts.spaceGrotesk(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        height: 34 / 28,
        letterSpacing: -0.02,
      );

  static TextStyle get headlineLg => GoogleFonts.spaceGrotesk(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        height: 32 / 24,
        letterSpacing: -0.02,
      );

  static TextStyle get headlineMd => GoogleFonts.spaceGrotesk(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        height: 26 / 20,
        letterSpacing: -0.01,
      );

  static TextStyle get headlineSm => GoogleFonts.spaceGrotesk(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        height: 24 / 18,
      );

  static TextStyle get bodyLg => GoogleFonts.plusJakartaSans(
        fontSize: 16,
        fontWeight: FontWeight.w500,
        height: 24 / 16,
      );

  static TextStyle get bodyMd => GoogleFonts.plusJakartaSans(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 20 / 14,
      );

  static TextStyle get bodySm => GoogleFonts.plusJakartaSans(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        height: 16 / 12,
      );

  static TextStyle get telemetryLg => GoogleFonts.jetBrainsMono(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        height: 22 / 18,
        letterSpacing: -0.02,
      );

  static TextStyle get telemetryMd => GoogleFonts.jetBrainsMono(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        height: 18 / 14,
      );

  static TextStyle get telemetrySm => GoogleFonts.jetBrainsMono(
        fontSize: 11,
        fontWeight: FontWeight.w500,
        height: 14 / 11,
        letterSpacing: 0.04,
      );

  static TextStyle get labelMd => GoogleFonts.plusJakartaSans(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        height: 16 / 12,
        letterSpacing: 0.02,
      );

  static TextStyle get labelSm => GoogleFonts.plusJakartaSans(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        height: 14 / 11,
        letterSpacing: 0.05,
      );

  static TextTheme get textTheme => TextTheme(
        displayLarge: displayLg,
        displayMedium: displayLgMobile,
        displaySmall: headlineLg,
        headlineLarge: headlineLg,
        headlineMedium: headlineMd,
        headlineSmall: headlineSm,
        titleLarge: headlineSm,
        titleMedium: bodyLg,
        titleSmall: labelMd,
        bodyLarge: bodyLg,
        bodyMedium: bodyMd,
        bodySmall: bodySm,
        labelLarge: labelMd,
        labelMedium: labelSm,
        labelSmall: labelSm,
      );

  static TextTheme get telemetryTextTheme => TextTheme(
        bodyLarge: telemetryLg,
        bodyMedium: telemetryMd,
        bodySmall: telemetrySm,
      );
}
