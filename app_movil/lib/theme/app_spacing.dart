import 'package:flutter/material.dart';

class AppSpacing {
  AppSpacing._();

  static const double spaceXs = 4.0;
  static const double spaceSm = 8.0;
  static const double spaceMd = 12.0;
  static const double spaceLg = 16.0;
  static const double spaceXl = 24.0;

  static const double gutter = 16.0;
  static const double gutterSm = 12.0;
  static const double gutterLg = 24.0;

  static const double margin = 16.0;
  static const double marginSm = 12.0;
  static const double marginLg = 24.0;

  static const double boardMargin = 16.0;

  static const EdgeInsets screenPadding = EdgeInsets.all(margin);
  static const EdgeInsets screenPaddingSm = EdgeInsets.all(marginSm);
  static const EdgeInsets screenPaddingLg = EdgeInsets.all(marginLg);

  static const EdgeInsets cardPadding = EdgeInsets.all(spaceLg);
  static const EdgeInsets cardPaddingSm = EdgeInsets.all(spaceMd);
  static const EdgeInsets cardPaddingMd = EdgeInsets.all(16.0);
  static const EdgeInsets cardPaddingLg = EdgeInsets.all(spaceXl);
}

class AppRadius {
  AppRadius._();

  static const double sm = 4.0;
  static const double base = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 24.0;
  static const double full = 9999.0;

  static const BorderRadius radiusSm = BorderRadius.all(Radius.circular(sm));
  static const BorderRadius radiusBase = BorderRadius.all(Radius.circular(base));
  static const BorderRadius radiusMd = BorderRadius.all(Radius.circular(md));
  static const BorderRadius radiusLg = BorderRadius.all(Radius.circular(lg));
  static const BorderRadius radiusXl = BorderRadius.all(Radius.circular(xl));
  static const BorderRadius radiusFull = BorderRadius.all(Radius.circular(full));

  static const BorderRadius boardRadius = BorderRadius.all(Radius.circular(lg));
}