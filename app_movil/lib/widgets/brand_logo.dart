import 'package:flutter/material.dart';
import '../theme.dart';

/// Logo de ChessIA (imagen + wordmark). Se usa en login y en la pantalla de
/// selección de modo; `size` es el lado de la imagen.
class BrandLogo extends StatelessWidget {
  final double size;
  final double fontSize;

  const BrandLogo({super.key, this.size = 150, this.fontSize = 43});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Image.asset(
          'assets/images/logo.png',
          width: size,
          height: size,
          fit: BoxFit.contain,
          semanticLabel: 'Logo ChessIA',
        ),
        const SizedBox(height: AppSpacing.spaceMd),
        Text.rich(
          TextSpan(
            style: TextStyle(
              fontFamily: 'SpaceGrotesk',
              fontSize: fontSize,
              fontWeight: FontWeight.w800,
              height: 1.0,
            ),
            children: const [
              TextSpan(text: 'Chess', style: TextStyle(color: AppColors.onSurface)),
              TextSpan(text: 'I', style: TextStyle(color: Color(0xFF15B271), fontWeight: FontWeight.w900)),
              TextSpan(text: 'A', style: TextStyle(color: Color(0xFFF28C28), fontWeight: FontWeight.w900)),
            ],
          ),
        ),
      ],
    );
  }
}
