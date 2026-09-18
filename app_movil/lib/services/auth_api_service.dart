import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api_config.dart';

/// Rol con el que la app móvil registra y valida a sus usuarios. La app es
/// solo para jugadores; una cuenta con otro rol no puede entrar desde acá.
const String rolJugador = 'jugador';

/// Cliente HTTP de `/auth/*` del backend FastAPI. Guarda los tokens JWT en
/// almacenamiento seguro y los reenvía en cada request; si el access token
/// vence, intenta renovarlo con el refresh token una sola vez.
class AuthApiService {
  static const _storage = FlutterSecureStorage();
  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';

  final Dio _dio;

  /// URL fija (tests); si es `null`, cada request usa `ApiConfig.baseUrl`.
  final String? _baseUrlFija;

  AuthApiService({String? baseUrl})
      : _baseUrlFija = baseUrl,
        _dio = Dio(BaseOptions(
          baseUrl: baseUrl ?? ApiConfig.baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        )) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        options.baseUrl = _baseUrlFija ?? ApiConfig.baseUrl;
        final accessToken = await _storage.read(key: _kAccess);
        if (accessToken != null) {
          options.headers['Authorization'] = 'Bearer $accessToken';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final esAuthPublica = error.requestOptions.path.startsWith('/auth/') &&
            !error.requestOptions.path.endsWith('/me');
        if (error.response?.statusCode == 401 && !esAuthPublica) {
          if (await _refreshToken()) {
            final accessToken = await _storage.read(key: _kAccess);
            error.requestOptions.headers['Authorization'] = 'Bearer $accessToken';
            return handler.resolve(await _dio.fetch(error.requestOptions));
          }
          await _clearTokens();
        }
        handler.next(error);
      },
    ));
  }

  Future<bool> _refreshToken() async {
    final refreshToken = await _storage.read(key: _kRefresh);
    if (refreshToken == null) return false;
    try {
      final response = await _dio.post('/auth/refresh', data: {'refresh_token': refreshToken});
      await _guardarTokens(response.data as Map<String, dynamic>);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> _guardarTokens(Map<String, dynamic> tokens) async {
    await _storage.write(key: _kAccess, value: tokens['access_token'] as String);
    await _storage.write(key: _kRefresh, value: tokens['refresh_token'] as String);
  }

  Future<void> _clearTokens() async {
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
  }

  /// Registra una cuenta nueva con rol `jugador` y deja la sesión iniciada.
  /// Devuelve el mapa `usuario` que responde el backend.
  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String nombre,
  }) async {
    final response = await _dio.post('/auth/registro', data: {
      'email': email,
      'password': password,
      'nombre': nombre,
      'rol': rolJugador,
    });
    final data = response.data as Map<String, dynamic>;
    await _guardarTokens(data['tokens'] as Map<String, dynamic>);
    return data['usuario'] as Map<String, dynamic>;
  }

  /// Inicia sesión exigiendo rol `jugador` (el backend responde 403 si la
  /// cuenta tiene otro rol). Devuelve el mapa `usuario`.
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await _dio.post('/auth/login', data: {
      'email': email,
      'password': password,
      'rol_esperado': rolJugador,
    });
    final data = response.data as Map<String, dynamic>;
    await _guardarTokens(data['tokens'] as Map<String, dynamic>);
    return data['usuario'] as Map<String, dynamic>;
  }

  Future<void> logout() async {
    await _clearTokens();
  }

  /// Guarda el resultado de "Mide tu nivel" (nivel/rango calculado) en el
  /// perfil del jugador — pisa el resultado anterior, no guarda historial.
  Future<void> guardarNivelEstimado({required int nivel, required String rango}) async {
    await _dio.patch('/auth/nivel-estimado', data: {'nivel': nivel, 'rango': rango});
  }

  Future<bool> hasStoredToken() async {
    return await _storage.read(key: _kAccess) != null;
  }

  /// Usuario de la sesión guardada, o `null` si el token ya no sirve.
  Future<Map<String, dynamic>?> getCurrentUser() async {
    try {
      final response = await _dio.get('/auth/me');
      return response.data as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  /// Mensaje legible para la UI: el `detail` de FastAPI si existe, o un
  /// aviso de conexión si el backend no responde.
  static String mensajeDeError(Object error) {
    if (error is DioException) {
      final detalle = error.response?.data;
      if (detalle is Map && detalle['detail'] != null) {
        final detail = detalle['detail'];
        if (detail is List && detail.isNotEmpty && detail.first is Map) {
          return (detail.first as Map)['msg']?.toString() ?? 'Datos inválidos';
        }
        return detail.toString();
      }
      if (error.type == DioExceptionType.connectionError ||
          error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.receiveTimeout) {
        return 'No se pudo conectar con el backend — ¿está corriendo?';
      }
    }
    return error.toString();
  }
}
