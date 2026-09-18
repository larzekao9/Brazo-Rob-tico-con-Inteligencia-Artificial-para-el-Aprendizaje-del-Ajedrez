import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'api_config.dart';
import 'partida.dart';

/// Cliente HTTP contra el backend FastAPI real (mismo backend que usa la
/// Sala de Control web) — sin datos simulados. No agrega endpoints nuevos:
/// solo consume los que ya existen en `backend/rutas/`.
class ChessApi {
  ChessApi._() : _dio = Dio(BaseOptions(baseUrl: ApiConfig.baseUrl, connectTimeout: const Duration(seconds: 5))) {
    // La URL puede cambiar en caliente desde la pantalla de login.
    _dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) {
      options.baseUrl = ApiConfig.baseUrl;
      handler.next(options);
    }));
  }

  /// Instancia global. En tests se reemplaza por una subclase falsa
  /// (ver `ChessApi.paraTests`) para no depender de la red.
  static ChessApi instancia = ChessApi._();

  /// Constructor para subclases de prueba; no usar en la app.
  @visibleForTesting
  ChessApi.paraTests() : this._();

  final Dio _dio;

  Future<bool> backendEnLinea() async {
    try {
      final respuesta = await _dio.get('/health');
      return respuesta.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Partida> crearPartida({required int nivel, String tipoOponente = 'motor', String? fenInicial}) async {
    final respuesta = await _dio.post('/partida', data: {
      'nivel': nivel,
      'tipo_oponente': tipoOponente,
      if (fenInicial != null) 'fen_inicial': fenInicial,
    });
    return Partida.fromJson(respuesta.data as Map<String, dynamic>);
  }

  Future<Partida> obtenerPartida(String partidaId) async {
    final respuesta = await _dio.get('/partida/$partidaId');
    return Partida.fromJson(respuesta.data as Map<String, dynamic>);
  }

  Future<List<String>> jugadasLegalesDesde(String partidaId, String casilla) async {
    final respuesta = await _dio.get('/partida/$partidaId/jugadas-legales', queryParameters: {'casilla': casilla});
    return List<String>.from((respuesta.data as Map<String, dynamic>)['casillas'] as List);
  }

  Future<ResultadoMovimiento> mover(String partidaId, String jugadaUci) async {
    final respuesta = await _dio.post('/partida/$partidaId/mover', data: {'jugada': jugadaUci});
    return ResultadoMovimiento.fromJson(respuesta.data as Map<String, dynamic>);
  }

  Future<AnalisisPosicion> analizarPosicion(String fen, int nivel) async {
    final respuesta = await _dio.post('/analisis', data: {'fen': fen, 'nivel': nivel});
    return AnalisisPosicion.fromJson(respuesta.data as Map<String, dynamic>);
  }

  /// Analiza cada jugada ya jugada de la partida contra Stockfish (HU5/HU6)
  /// — lento (un proceso de Stockfish por posición), se llama una sola vez
  /// al terminar la partida, no durante la jugada en vivo.
  Future<List<JugadaAnalisis>> analisisCompleto(String partidaId) async {
    final respuesta = await _dio.get(
      '/partida/$partidaId/analisis-completo',
      options: Options(sendTimeout: const Duration(seconds: 30), receiveTimeout: const Duration(seconds: 30)),
    );
    final jugadas = (respuesta.data as Map<String, dynamic>)['jugadas'] as List;
    return jugadas.map((j) => JugadaAnalisis.fromJson(j as Map<String, dynamic>)).toList();
  }

  /// Extrae el mensaje de error real que manda el backend (`detail` de
  /// FastAPI) en vez del texto genérico de Dio, para mostrarlo en la UI.
  static String mensajeDeError(Object error) {
    if (error is DioException) {
      final detalle = error.response?.data;
      if (detalle is Map && detalle['detail'] != null) {
        return detalle['detail'].toString();
      }
      if (error.type == DioExceptionType.connectionError ||
          error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.receiveTimeout) {
        return 'No se pudo conectar con el backend — ¿está corriendo?';
      }
      final codigo = error.response?.statusCode;
      if (codigo != null) return 'Error del backend (HTTP $codigo)';
      return 'Error de red: ${error.message ?? error.type.name}';
    }
    return error.toString();
  }
}
