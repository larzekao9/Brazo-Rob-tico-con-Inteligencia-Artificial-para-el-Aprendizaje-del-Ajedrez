/// Modelos que reflejan los esquemas Pydantic reales del backend
/// (`backend/esquemas/partida_esquema.py`, `jugada_esquema.py`) — nada de
/// datos simulados, cada campo viene tal cual del JSON que devuelve FastAPI.
class Partida {
  final String id;
  final String tipoOponente;
  final int nivel;
  final String fen;
  final String fenInicial;
  final bool terminada;
  final String? resultado;
  final List<String> jugadas;

  Partida({
    required this.id,
    required this.tipoOponente,
    required this.nivel,
    required this.fen,
    required this.fenInicial,
    required this.terminada,
    required this.resultado,
    required this.jugadas,
  });

  factory Partida.fromJson(Map<String, dynamic> json) => Partida(
        id: json['id'] as String,
        tipoOponente: json['tipo_oponente'] as String,
        nivel: json['nivel'] as int,
        fen: json['fen'] as String,
        fenInicial: json['fen_inicial'] as String? ?? json['fen'] as String,
        terminada: json['terminada'] as bool,
        resultado: json['resultado'] as String?,
        jugadas: List<String>.from(json['jugadas'] as List? ?? const []),
      );
}

class ResultadoMovimiento {
  final String fen;
  final String? jugadaMotor;
  final bool terminada;
  final String? resultado;
  final List<String> jugadas;

  ResultadoMovimiento({
    required this.fen,
    required this.jugadaMotor,
    required this.terminada,
    required this.resultado,
    required this.jugadas,
  });

  factory ResultadoMovimiento.fromJson(Map<String, dynamic> json) => ResultadoMovimiento(
        fen: json['fen'] as String,
        jugadaMotor: json['jugada_motor'] as String?,
        terminada: json['terminada'] as bool,
        resultado: json['resultado'] as String?,
        jugadas: List<String>.from(json['jugadas'] as List? ?? const []),
      );
}

class AnalisisPosicion {
  final String? jugada;
  final int? evaluacionCp;
  final int? mateEn;

  AnalisisPosicion({required this.jugada, required this.evaluacionCp, required this.mateEn});

  factory AnalisisPosicion.fromJson(Map<String, dynamic> json) => AnalisisPosicion(
        jugada: json['jugada'] as String?,
        evaluacionCp: json['evaluacion_cp'] as int?,
        mateEn: json['mate_en'] as int?,
      );

  /// El backend devuelve `evaluacion_cp`/`mate_en` desde la perspectiva de
  /// quien mueve en esa posición (ver motor_ajedrez.analizar_posicion), no
  /// siempre blancas. `turnoQueMueve` es 'w' o 'b' — se usa para reexpresar
  /// el valor en perspectiva de blancas, que es como se dibuja la barra.
  double evaluacionBlancasEnPeones(String turnoQueMueve) {
    final signo = turnoQueMueve == 'b' ? -1 : 1;
    if (mateEn != null) return (mateEn! > 0 ? 9.0 : -9.0) * signo;
    return ((evaluacionCp ?? 0) / 100.0) * signo;
  }
}

/// Una jugada ya jugada, analizada por Stockfish — de GET /partida/{id}/analisis-completo.
class JugadaAnalisis {
  final int numeroPly;
  final String color; // "blanco" o "negro"
  final String jugadaSan;
  final String? mejorJugadaMotor;

  JugadaAnalisis({
    required this.numeroPly,
    required this.color,
    required this.jugadaSan,
    required this.mejorJugadaMotor,
  });

  factory JugadaAnalisis.fromJson(Map<String, dynamic> json) => JugadaAnalisis(
        numeroPly: json['numero_ply'] as int,
        color: json['color'] as String,
        jugadaSan: json['jugada_san'] as String,
        mejorJugadaMotor: json['mejor_jugada_motor'] as String?,
      );
}

/// Cuenta de un tipo de error dentro de `top_errores` (GET /usuario/estadisticas).
class TopError {
  final String tipo; // "blunder" | "error" | "inexactitud"
  final int cantidad;

  const TopError({required this.tipo, required this.cantidad});

  factory TopError.fromJson(Map<String, dynamic> json) => TopError(
        tipo: json['tipo'] as String,
        cantidad: json['cantidad'] as int,
      );
}

/// Estadísticas agregadas del jugador real — de GET /usuario/estadisticas;
/// la app ya no usa valores de ejemplo en la página principal.
class EstadisticasUsuario {
  final int totalPartidas;
  final int partidasGanadas;
  final int partidasPerdidas;
  final int partidasTablas;
  final double winPercentPromedio;
  final int rachaVictoriaActual;

  /// Porcentaje de jugadas del jugador dentro del umbral de inexactitud del
  /// análisis de Stockfish (ver `servicio_estadisticas.py` en el backend).
  final double precisionPromedio;
  final List<TopError> topErrores;

  const EstadisticasUsuario({
    required this.totalPartidas,
    required this.partidasGanadas,
    required this.partidasPerdidas,
    required this.partidasTablas,
    required this.winPercentPromedio,
    required this.rachaVictoriaActual,
    required this.precisionPromedio,
    required this.topErrores,
  });

  factory EstadisticasUsuario.fromJson(Map<String, dynamic> json) => EstadisticasUsuario(
        totalPartidas: json['total_partidas'] as int,
        partidasGanadas: json['partidas_ganadas'] as int,
        partidasPerdidas: json['partidas_perdidas'] as int,
        partidasTablas: json['partidas_tablas'] as int,
        winPercentPromedio: (json['win_percent_promedio'] as num).toDouble(),
        rachaVictoriaActual: json['racha_victoria_actual'] as int,
        precisionPromedio: (json['precision_promedio'] as num).toDouble(),
        topErrores: [
          for (final item in json['top_errores'] as List? ?? const [])
            TopError.fromJson(item as Map<String, dynamic>),
        ],
      );
}
