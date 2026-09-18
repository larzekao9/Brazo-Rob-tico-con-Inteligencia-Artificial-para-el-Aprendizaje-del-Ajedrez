import 'package:flutter/material.dart';
import '../theme.dart';

/// Tablero de ajedrez real (lee un FEN, resalta selección/jugadas legales) —
/// la misma vista la usan la partida normal, el diagnóstico ("Mide tu
/// nivel") y, a futuro, el modo de enseñanza. Lo que varía entre esos flujos
/// es la lógica de arriba (qué pasa al tocar una casilla, qué panel se
/// muestra alrededor), no el tablero en sí.
class ChessBoard extends StatelessWidget {
  final String fen;
  final String? casillaOrigen;
  final List<String> destinosValidos;
  final void Function(String casilla) onTapCasilla;

  const ChessBoard({
    super.key,
    required this.fen,
    required this.casillaOrigen,
    required this.destinosValidos,
    required this.onTapCasilla,
  });

  static const Map<String, String> _simboloPieza = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
  };

  List<List<String?>> _fenAMatriz() {
    return fen.split(' ')[0].split('/').map((filaFen) {
      final fila = <String?>[];
      for (final caracter in filaFen.split('')) {
        final n = int.tryParse(caracter);
        if (n != null) {
          fila.addAll(List<String?>.filled(n, null));
        } else {
          fila.add(caracter);
        }
      }
      return fila;
    }).toList();
  }

  /// Relleno + contorno en un solo `Text` (vía `shadows` en 4 direcciones,
  /// no un segundo Text superpuesto) — piezas blancas con relleno blanco y
  /// borde oscuro, negras sólidas con borde claro, se distinguen bien sobre
  /// cualquiera de los dos colores de casilla sin depender de assets. Un
  /// solo widget de texto por pieza mantiene `find.text('♔')` único para
  /// los tests de este tablero.
  Widget _piezaWidget(String pieza, double casillaSize) {
    final esBlanca = pieza == pieza.toUpperCase();
    final glifo = _simboloPieza[pieza] ?? '';
    final colorBorde = esBlanca ? Colors.black87 : Colors.white70;
    return Text(
      glifo,
      style: TextStyle(
        fontSize: casillaSize * 0.62,
        color: esBlanca ? Colors.white : Colors.black,
        shadows: [
          Shadow(color: colorBorde, offset: const Offset(-1, -1)),
          Shadow(color: colorBorde, offset: const Offset(1, -1)),
          Shadow(color: colorBorde, offset: const Offset(-1, 1)),
          Shadow(color: colorBorde, offset: const Offset(1, 1)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final chessTheme = Theme.of(context).extension<ChessThemeExtension>()!;
    final matriz = _fenAMatriz();

    return AspectRatio(
      aspectRatio: 1,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: AppRadius.boardRadius,
          border: Border.all(color: AppColors.outlineVariant, width: 2),
          boxShadow: AppShadows.level2,
        ),
        child: ClipRRect(
          borderRadius: AppRadius.boardRadius,
          child: Stack(
            children: [
              LayoutBuilder(
                builder: (context, constraints) {
                  final casillaSize = constraints.maxWidth / 8;
                  return GridView.builder(
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 8),
                    itemCount: 64,
                    itemBuilder: (context, index) {
                      final fila = index ~/ 8;
                      final columna = index % 8;
                      final isLight = (fila + columna) % 2 == 0;
                      final casilla = '${'abcdefgh'[columna]}${8 - fila}';
                      final pieza = matriz[fila][columna];
                      final esOrigen = casilla == casillaOrigen;
                      final esDestino = destinosValidos.contains(casilla);

                      return GestureDetector(
                        onTap: () => onTapCasilla(casilla),
                        child: Container(
                          color: isLight ? chessTheme.whiteSquare : chessTheme.blackSquare,
                          child: Stack(
                            alignment: Alignment.center,
                            children: [
                              if (pieza != null) _piezaWidget(pieza, casillaSize),
                              if (esOrigen)
                                Container(
                                  margin: const EdgeInsets.all(2),
                                  decoration: BoxDecoration(
                                    border: Border.all(color: AppColors.primary, width: 3),
                                  ),
                                ),
                              if (esDestino && pieza == null)
                                Container(
                                  width: 14,
                                  height: 14,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: AppColors.primary.withOpacity(0.7),
                                  ),
                                ),
                              if (esDestino && pieza != null)
                                Container(
                                  margin: const EdgeInsets.all(3),
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    border: Border.all(color: AppColors.primary.withOpacity(0.85), width: 3),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      );
                    },
                  );
                },
              ),
              const _CoordinatesOverlay(),
            ],
          ),
        ),
      ),
    );
  }
}

class _CoordinatesOverlay extends StatelessWidget {
  const _CoordinatesOverlay();

  /// Un rótulo por casilla: ocupa la misma fracción que la casilla y se
  /// encoge si la fuente es más grande de lo esperado (nunca desborda).
  Widget _rotulo(String texto, Alignment alineacion) {
    return Expanded(
      child: Align(
        alignment: alineacion,
        child: FittedBox(
          fit: BoxFit.scaleDown,
          child: Padding(
            padding: const EdgeInsets.all(2),
            child: Text(
              texto,
              style: AppTextStyles.telemetrySm.copyWith(color: AppColors.onSurfaceVariant),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Stack(
        children: [
          Positioned.fill(
            child: Row(
              children: List.generate(
                8,
                (i) => _rotulo(String.fromCharCode(97 + i), Alignment.bottomRight),
              ),
            ),
          ),
          Positioned.fill(
            child: Column(
              children: List.generate(8, (i) => _rotulo('${8 - i}', Alignment.topLeft)),
            ),
          ),
        ],
      ),
    );
  }
}
