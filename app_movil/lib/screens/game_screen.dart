import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../widgets.dart';
import '../models.dart';
import '../services/chess_api.dart';

class GameScreen extends StatefulWidget {
  final String partidaId;
  final OpponentType opponent;
  final int level;
  final bool enableFeedback;

  /// Si viene de "Mide tu nivel" (mode_selection_screen): al terminar (o
  /// rendirse) no va a victoria/derrota, sino que juega `diagnosticoTotalRondas`
  /// partidas cortas seguidas y termina en /evaluation-result con un nivel
  /// calculado según cómo jugó de verdad — no un cuestionario.
  final bool esDiagnostico;
  final int diagnosticoRonda;
  final int diagnosticoTotalRondas;

  /// Precisión (0-100) de las rondas de diagnóstico ya jugadas antes de esta.
  final List<double> diagnosticoPrecisiones;

  const GameScreen({
    super.key,
    required this.partidaId,
    required this.opponent,
    required this.level,
    required this.enableFeedback,
    this.esDiagnostico = false,
    this.diagnosticoRonda = 1,
    this.diagnosticoTotalRondas = 1,
    this.diagnosticoPrecisiones = const [],
  });

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  static const _tiempoInicial = Duration(minutes: 10);

  String _fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  List<String> _jugadas = [];
  bool _terminada = false;
  String? _resultado;
  String? _casillaOrigen;
  List<String> _destinosValidos = [];
  double? _evaluacion;
  final List<double> _evaluacionHistorial = [];
  String? _mejorJugada;
  bool _cargandoInicial = true;
  bool _cargandoMovimiento = false;
  bool _cargandoFinal = false;
  String? _error;

  Timer? _timer;
  Duration _tiempoRestante = _tiempoInicial;

  @override
  void initState() {
    super.initState();
    _cargarPartida();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  /// Cronómetro real (cuenta segundos de verdad) pero decorativo: el backend
  /// no tiene control de tiempo, así que llegar a 0 no termina la partida.
  void _tick() {
    if (!mounted || _terminada || _cargandoMovimiento || _tiempoRestante == Duration.zero) return;
    setState(() => _tiempoRestante -= const Duration(seconds: 1));
  }

  Future<void> _cargarPartida() async {
    try {
      final partida = await ChessApi.instancia.obtenerPartida(widget.partidaId);
      if (!mounted) return;
      setState(() {
        _fen = partida.fen;
        _jugadas = partida.jugadas;
        _terminada = partida.terminada;
        _resultado = partida.resultado;
      });
      if (!partida.terminada && widget.enableFeedback) {
        await _actualizarAnalisis(partida.fen);
      }
    } catch (error) {
      if (mounted) setState(() => _error = ChessApi.mensajeDeError(error));
    } finally {
      if (mounted) setState(() => _cargandoInicial = false);
    }
  }

  Future<void> _actualizarAnalisis(String fen) async {
    try {
      final analisis = await ChessApi.instancia.analizarPosicion(fen, widget.level);
      if (!mounted) return;
      final evalBlancas = analisis.evaluacionBlancasEnPeones(_turnoDeFen(fen));
      setState(() {
        _evaluacion = evalBlancas;
        _mejorJugada = analisis.jugada;
        _evaluacionHistorial.add(evalBlancas);
      });
    } catch (_) {
      // El análisis es un plus visual — si Stockfish tarda o falla no bloqueamos el juego.
    }
  }

  String _turnoDeFen(String fen) => fen.split(' ')[1] == 'b' ? 'b' : 'w';

  List<List<String?>> _fenAMatriz(String fen) {
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

  String? _piezaEnCasilla(String casilla) {
    final matriz = _fenAMatriz(_fen);
    final columna = 'abcdefgh'.indexOf(casilla[0]);
    final fila = 8 - int.parse(casilla[1]);
    return matriz[fila][columna];
  }

  bool _esPiezaDelTurno(String casilla) {
    final pieza = _piezaEnCasilla(casilla);
    if (pieza == null) return false;
    final esBlanca = pieza == pieza.toUpperCase();
    final turno = _turnoDeFen(_fen);
    return esBlanca ? turno == 'w' : turno == 'b';
  }

  bool _esPromocionDePeon(String origen, String destino) {
    final pieza = _piezaEnCasilla(origen);
    final promocionBlancas = pieza == 'P' && origen[1] == '7' && destino.endsWith('8');
    final promocionNegras = pieza == 'p' && origen[1] == '2' && destino.endsWith('1');
    return promocionBlancas || promocionNegras;
  }

  Future<void> _seleccionarOrigen(String casilla) async {
    setState(() {
      _casillaOrigen = casilla;
      _destinosValidos = [];
    });
    try {
      final destinos = await ChessApi.instancia.jugadasLegalesDesde(widget.partidaId, casilla);
      if (!mounted) return;
      setState(() => _destinosValidos = destinos);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = ChessApi.mensajeDeError(error));
    }
  }

  Future<void> _manejarClicCasilla(String casilla) async {
    if (_terminada || _cargandoMovimiento) return;

    if (_casillaOrigen == null) {
      if (_esPiezaDelTurno(casilla)) await _seleccionarOrigen(casilla);
      return;
    }

    final origen = _casillaOrigen!;
    if (origen == casilla) {
      setState(() {
        _casillaOrigen = null;
        _destinosValidos = [];
      });
      return;
    }

    if (_esPiezaDelTurno(casilla)) {
      await _seleccionarOrigen(casilla);
      return;
    }

    setState(() {
      _casillaOrigen = null;
      _destinosValidos = [];
      _cargandoMovimiento = true;
      _error = null;
    });

    final jugadaUci = '$origen$casilla${_esPromocionDePeon(origen, casilla) ? 'q' : ''}';

    try {
      final resultado = await ChessApi.instancia.mover(widget.partidaId, jugadaUci);
      if (!mounted) return;
      setState(() {
        _fen = resultado.fen;
        _jugadas = resultado.jugadas;
        _terminada = resultado.terminada;
        _resultado = resultado.resultado;
      });
      if (resultado.terminada) {
        await _manejarFinDePartida();
      } else if (widget.enableFeedback) {
        await _actualizarAnalisis(resultado.fen);
      }
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = ChessApi.mensajeDeError(error));
    } finally {
      if (mounted) setState(() => _cargandoMovimiento = false);
    }
  }

  Future<double> _calcularPrecisionBlancas() async {
    try {
      final analisis = await ChessApi.instancia.analisisCompleto(widget.partidaId);
      final jugadasBlancas = analisis.where((j) => j.color == 'blanco').toList();
      if (jugadasBlancas.isEmpty) return 0;
      final aciertos = jugadasBlancas.where((j) => j.jugadaSan == j.mejorJugadaMotor).length;
      return aciertos / jugadasBlancas.length * 100;
    } catch (_) {
      // Si el análisis completo falla (partida larga, timeout) seguimos sin precisión.
      return 0;
    }
  }

  Future<void> _manejarFinDePartida() async {
    setState(() => _cargandoFinal = true);
    final accuracy = await _calcularPrecisionBlancas();
    if (!mounted) return;
    setState(() => _cargandoFinal = false);

    if (widget.esDiagnostico) {
      await _avanzarDiagnostico(accuracy);
      return;
    }

    final opponentLabel = widget.opponent == OpponentType.model ? 'Modelo IA' : 'Stockfish';
    final extra = {
      'playerName': 'Jugador',
      'accuracy': accuracy.round(),
      'moves': _jugadas.length,
      'finalEval': _evaluacion ?? 0.0,
      'opponent': opponentLabel,
    };

    if (_resultado == '1-0') {
      context.go('/victory', extra: extra);
    } else if (_resultado == '0-1') {
      context.go('/defeat', extra: extra);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Partida terminada en tablas')),
      );
      context.go('/home');
    }
  }

  /// Rendirse en modo diagnóstico igual evalúa las jugadas que sí se
  /// llegaron a hacer — no hace falta terminar la partida para tener una
  /// precisión real (analisis-completo solo mira las jugadas ya jugadas).
  Future<void> _rendirseEnDiagnostico() async {
    setState(() => _cargandoFinal = true);
    final accuracy = await _calcularPrecisionBlancas();
    if (!mounted) return;
    setState(() => _cargandoFinal = false);
    await _avanzarDiagnostico(accuracy);
  }

  /// Si todavía faltan rondas, arranca la siguiente partida corta; si esta
  /// era la última, promedia la precisión de todas las rondas jugadas y
  /// muestra el resultado final.
  Future<void> _avanzarDiagnostico(double accuracyDeEstaRonda) async {
    final precisiones = [...widget.diagnosticoPrecisiones, accuracyDeEstaRonda];

    if (widget.diagnosticoRonda >= widget.diagnosticoTotalRondas) {
      final promedio = precisiones.reduce((a, b) => a + b) / precisiones.length;
      _irAResultadoDiagnostico(promedio);
      return;
    }

    try {
      final siguiente = await ChessApi.instancia.crearPartida(nivel: widget.level, tipoOponente: 'motor');
      if (!mounted) return;
      context.go('/game', extra: {
        'partidaId': siguiente.id,
        'opponent': widget.opponent,
        'level': widget.level,
        'enableFeedback': widget.enableFeedback,
        'esDiagnostico': true,
        'diagnosticoRonda': widget.diagnosticoRonda + 1,
        'diagnosticoTotalRondas': widget.diagnosticoTotalRondas,
        'diagnosticoPrecisiones': precisiones,
      });
    } catch (error) {
      if (!mounted) return;
      // No se pudo armar la siguiente ronda — mostramos el resultado con lo que hay hasta ahora.
      final promedio = precisiones.reduce((a, b) => a + b) / precisiones.length;
      _irAResultadoDiagnostico(promedio);
    }
  }

  void _irAResultadoDiagnostico(double accuracy) {
    String rank;
    int nivelAsignado;
    if (accuracy >= 80) {
      rank = 'Avanzado';
      nivelAsignado = 18;
    } else if (accuracy >= 55) {
      rank = 'Intermedio';
      nivelAsignado = 11;
    } else {
      rank = 'Principiante';
      nivelAsignado = 5;
    }

    context.go('/evaluation-result', extra: {
      'level': nivelAsignado,
      'rank': rank,
      'accuracy': accuracy,
      'gamesPlayed': widget.diagnosticoTotalRondas,
    });
  }

  List<MoveEntry> _historialDeJugadas() {
    final entradas = <MoveEntry>[];
    for (int i = 0; i < _jugadas.length; i += 2) {
      entradas.add(MoveEntry(
        moveNumber: i ~/ 2 + 1,
        whiteMove: _jugadas[i],
        blackMove: i + 1 < _jugadas.length ? _jugadas[i + 1] : null,
      ));
    }
    return entradas;
  }

  @override
  Widget build(BuildContext context) {
    if (_cargandoInicial) {
      return const Scaffold(
        backgroundColor: AppColors.background,
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final historial = _historialDeJugadas();
    final progresoRonda = ((widget.diagnosticoRonda - 1) + (_jugadas.length / 16).clamp(0, 1)) /
        widget.diagnosticoTotalRondas;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _TopBar(
              opponent: widget.opponent,
              level: widget.level,
              esDiagnostico: widget.esDiagnostico,
              onMenuTap: _showMenu,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.margin),
                child: Column(
                  children: [
                    if (_error != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.spaceMd),
                        child: Text(
                          _error!,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: AppTextStyles.bodySm.copyWith(color: AppColors.moveBlunder),
                        ),
                      ),
                    if (widget.esDiagnostico && widget.diagnosticoTotalRondas > 1) ...[
                      EvaluationRoundProgress(
                        ronda: widget.diagnosticoRonda,
                        totalRondas: widget.diagnosticoTotalRondas,
                        progreso: progresoRonda,
                        evaluacionActual: widget.enableFeedback ? _evaluacion : null,
                      ),
                      const SizedBox(height: AppSpacing.spaceMd),
                    ],
                    TurnStatusCard(
                      esTurnoBlancas: _turnoDeFen(_fen) == 'w',
                      tiempoRestante: _tiempoRestante,
                    ),
                    const SizedBox(height: AppSpacing.spaceMd),
                    if (widget.enableFeedback) ...[
                      EvaluationBar(evaluation: _evaluacion ?? 0.0, isWhitePerspective: true, height: 14),
                      const SizedBox(height: AppSpacing.spaceMd),
                    ],
                    if (_cargandoFinal)
                      const Padding(
                        padding: EdgeInsets.only(bottom: AppSpacing.spaceMd),
                        child: LinearProgressIndicator(),
                      ),
                    ChessBoard(
                      fen: _fen,
                      casillaOrigen: _casillaOrigen,
                      destinosValidos: _destinosValidos,
                      onTapCasilla: _manejarClicCasilla,
                    ),
                    const SizedBox(height: AppSpacing.spaceLg),
                    if (widget.enableFeedback) ...[
                      _AnalysisPanel(evaluation: _evaluacion ?? 0.0, bestMove: _mejorJugada),
                      const SizedBox(height: AppSpacing.spaceLg),
                      TacticalCard(
                        title: 'Curva de ventaja (esta partida)',
                        child: EvaluationHistoryChart(valores: _evaluacionHistorial),
                      ),
                      const SizedBox(height: AppSpacing.spaceLg),
                      MoveHistory(
                        moves: historial,
                        highlightedIndex: historial.isEmpty ? null : historial.length - 1,
                      ),
                    ],
                    const SizedBox(height: AppSpacing.spaceLg),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showMenu() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => _GameMenuSheet(
        onRendirse: () {
          Navigator.pop(context);
          if (widget.esDiagnostico) {
            _rendirseEnDiagnostico();
          } else {
            context.go('/home');
          }
        },
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  final OpponentType opponent;
  final int level;
  final bool esDiagnostico;
  final VoidCallback onMenuTap;

  const _TopBar({
    required this.opponent,
    required this.level,
    required this.esDiagnostico,
    required this.onMenuTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.margin),
      child: Row(
        children: [
          IconButton(
            onPressed: onMenuTap,
            icon: const Icon(Icons.menu, color: AppColors.onSurface),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  esDiagnostico ? 'Mide tu nivel' : (opponent == OpponentType.stockfish ? 'Stockfish' : 'Modelo IA'),
                  style: AppTextStyles.headlineSm.copyWith(color: AppColors.onSurface),
                ),
                Text(
                  esDiagnostico ? 'Jugá tu mejor partida — así calculamos tu nivel' : 'Nivel $level',
                  style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant),
                ),
              ],
            ),
          ),
          GlassCard(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.spaceMd,
              vertical: AppSpacing.spaceXs,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: AppColors.clockActive,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: AppSpacing.spaceXs),
                Text(
                  'En juego',
                  style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurface),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AnalysisPanel extends StatelessWidget {
  final double evaluation;
  final String? bestMove;

  const _AnalysisPanel({
    required this.evaluation,
    required this.bestMove,
  });

  static double _sigmoide(double x) {
    double resultado = 1.0, termino = 1.0;
    for (int i = 1; i < 30; i++) {
      termino *= x / i;
      resultado += termino;
    }
    return resultado;
  }

  @override
  Widget build(BuildContext context) {
    final evalText = evaluation > 0 ? '+${evaluation.toStringAsFixed(1)}' : evaluation.toStringAsFixed(1);
    final isMate = evaluation.abs() >= 9;
    final winPercent = (50 + 50 * (2 / (1 + _sigmoide(-0.00368208 * evaluation * 100)) - 1)).round();

    return TacticalCard(
      title: 'Análisis de la posición',
      titleTrailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.spaceSm, vertical: 2),
        decoration: BoxDecoration(color: AppColors.primaryContainer, borderRadius: AppRadius.radiusFull),
        child: Text('Stockfish', style: AppTextStyles.labelSm.copyWith(color: AppColors.primary)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Evaluación', style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant)),
                const SizedBox(height: 2),
                Text(
                  isMate ? 'MATE' : evalText,
                  style: AppTextStyles.telemetryLg.copyWith(
                    color: evaluation > 0 ? AppColors.primary : AppColors.onSurface,
                  ),
                ),
              ],
            ),
          ),
          Container(
            width: 1,
            height: 40,
            color: AppColors.outlineVariant,
            margin: const EdgeInsets.symmetric(horizontal: AppSpacing.spaceLg),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Mejor jugada', style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant)),
                const SizedBox(height: 2),
                Text(
                  (bestMove ?? '—').toUpperCase(),
                  style: AppTextStyles.telemetryLg.copyWith(color: AppColors.secondary),
                ),
              ],
            ),
          ),
          Container(
            width: 1,
            height: 40,
            color: AppColors.outlineVariant,
            margin: const EdgeInsets.symmetric(horizontal: AppSpacing.spaceLg),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Equilibrio', style: AppTextStyles.labelSm.copyWith(color: AppColors.onSurfaceVariant)),
                const SizedBox(height: 2),
                Text(
                  '$winPercent%',
                  style: AppTextStyles.telemetryLg.copyWith(
                    color: evaluation > 0 ? AppColors.primary : AppColors.moveMistake,
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

class _GameMenuSheet extends StatelessWidget {
  final VoidCallback onRendirse;

  const _GameMenuSheet({required this.onRendirse});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      margin: const EdgeInsets.all(AppSpacing.margin),
      borderRadius: AppRadius.radiusXl,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _MenuTile(
            icon: Icons.pause,
            title: 'Pausar',
            subtitle: 'Detener el reloj',
            onTap: () => Navigator.pop(context),
          ),
          _MenuTile(
            icon: Icons.settings,
            title: 'Configuración',
            subtitle: 'Sonidos, tablero, notaciones',
            onTap: () => Navigator.pop(context),
          ),
          _MenuTile(
            icon: Icons.help_outline,
            title: 'Ayuda',
            subtitle: 'Reglas, atajos, contacto',
            onTap: () => Navigator.pop(context),
          ),
          const Divider(height: 1, color: AppColors.outlineVariant),
          _MenuTile(
            icon: Icons.flag,
            title: 'Rendirse',
            subtitle: 'Terminar la partida',
            isDestructive: true,
            onTap: onRendirse,
          ),
        ],
      ),
    );
  }
}

class _MenuTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool isDestructive;
  final VoidCallback onTap;

  const _MenuTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.isDestructive = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: isDestructive ? AppColors.moveBlunder : AppColors.onSurface),
      title: Text(
        title,
        style: AppTextStyles.bodyLg.copyWith(color: isDestructive ? AppColors.moveBlunder : AppColors.onSurface),
      ),
      subtitle: Text(subtitle, style: AppTextStyles.bodySm.copyWith(color: AppColors.onSurfaceVariant)),
      onTap: onTap,
    );
  }
}
