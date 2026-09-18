import 'package:flutter/material.dart';
import 'app_colors.dart';

class AppShadows {
  AppShadows._();

  static const List<BoxShadow> level0 = [];

  static const List<BoxShadow> level1 = [
    BoxShadow(
      color: Color(0x0A0F172A),
      offset: Offset(0, 2),
      blurRadius: 8,
      spreadRadius: -2,
    ),
  ];

  static const List<BoxShadow> level2 = [
    BoxShadow(
      color: Color(0x0F087F5B),
      offset: Offset(0, 4),
      blurRadius: 16,
      spreadRadius: -4,
    ),
    BoxShadow(
      color: Color(0x080F172A),
      offset: Offset(0, 2),
      blurRadius: 4,
      spreadRadius: -1,
    ),
  ];

  static const List<BoxShadow> level3 = [
    BoxShadow(
      color: Color(0x14087F5B),
      offset: Offset(0, 8),
      blurRadius: 24,
      spreadRadius: -4,
    ),
    BoxShadow(
      color: Color(0x0A0F172A),
      offset: Offset(0, 4),
      blurRadius: 8,
      spreadRadius: -2,
    ),
  ];

  static List<BoxShadow> neuralCyanGlow({double radius = 16}) => [
    BoxShadow(
      color: AppColors.neuralCyanGlow,
      blurRadius: radius,
      spreadRadius: 0,
    ),
  ];

  static List<BoxShadow> neuralAmberGlow({double radius = 16}) => [
    BoxShadow(
      color: AppColors.neuralAmberGlow,
      blurRadius: radius,
      spreadRadius: 0,
    ),
  ];

  static List<BoxShadow> glassMorphic() => [
    BoxShadow(
      color: AppColors.surfaceGlassBorder.withOpacity(0.5),
      offset: const Offset(0, 1),
      blurRadius: 2,
      spreadRadius: 0,
    ),
    BoxShadow(
      color: Colors.black.withOpacity(0.04),
      offset: const Offset(0, 8),
      blurRadius: 24,
      spreadRadius: -4,
    ),
  ];
}