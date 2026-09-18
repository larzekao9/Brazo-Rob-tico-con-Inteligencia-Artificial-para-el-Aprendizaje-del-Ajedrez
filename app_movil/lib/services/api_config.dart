import 'dart:io' show Platform;

import 'package:shared_preferences/shared_preferences.dart';

/// URL base del backend FastAPI, compartida por `ChessApi` y `AuthApiService`.
///
/// Orden de prioridad:
/// 1. URL guardada en el dispositivo desde la pantalla de login (sirve para
///    cambiar la IP de la Mac sin recompilar, p. ej. en la red de la U).
/// 2. `--dart-define=API_BASE_URL=http://192.168.x.x:8000` al compilar.
/// 3. Emulador de Android: `10.0.2.2` es el alias de la máquina anfitriona.
/// 4. iOS/macOS: `127.0.0.1` (solo sirve en simulador; en un iPhone físico
///    hay que usar 1 o 2).
///
/// Los clientes Dio leen `baseUrl` en cada request (ver sus interceptores),
/// así que un cambio hecho con `guardar` aplica de inmediato.
class ApiConfig {
  ApiConfig._();

  static const _kServidor = 'api_base_url';
  static const String _desdeEntorno = String.fromEnvironment('API_BASE_URL');
  static String? _guardada;

  static String get porDefecto {
    if (_desdeEntorno.isNotEmpty) return _desdeEntorno;
    if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    return 'http://127.0.0.1:8000';
  }

  static String get baseUrl => _guardada ?? porDefecto;

  /// `true` si el usuario dejó una URL propia (distinta de la por defecto).
  static bool get tieneOverride => _guardada != null;

  /// Lee la URL guardada en el dispositivo. Llamar una vez al arrancar.
  static Future<void> cargar() async {
    final prefs = await SharedPreferences.getInstance();
    _guardada = prefs.getString(_kServidor);
  }

  /// Guarda una URL propia, o vuelve a la por defecto si `url` es vacía/nula.
  static Future<void> guardar(String? url) async {
    final prefs = await SharedPreferences.getInstance();
    final limpia = normalizar(url);
    if (limpia == null) {
      _guardada = null;
      await prefs.remove(_kServidor);
    } else {
      _guardada = limpia;
      await prefs.setString(_kServidor, limpia);
    }
  }

  /// Quita espacios y barra final, y agrega `http://` si falta el esquema.
  /// Devuelve `null` para una entrada vacía.
  static String? normalizar(String? url) {
    var limpia = (url ?? '').trim();
    if (limpia.isEmpty) return null;
    if (!limpia.startsWith('http://') && !limpia.startsWith('https://')) {
      limpia = 'http://$limpia';
    }
    while (limpia.endsWith('/')) {
      limpia = limpia.substring(0, limpia.length - 1);
    }
    return limpia;
  }
}
