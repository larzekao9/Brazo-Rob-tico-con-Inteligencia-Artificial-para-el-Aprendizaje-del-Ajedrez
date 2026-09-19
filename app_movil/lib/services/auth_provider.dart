import 'package:flutter/foundation.dart';

import 'auth_api_service.dart';
import 'partida.dart';

/// Usuario autenticado tal como lo devuelve `/auth/me`, `/auth/login` y
/// `/auth/registro` del backend.
class AppUser {
  final int id;
  final String email;
  final String nombre;
  final String rol;
  final int? nivelEstimado;
  final String? rangoEstimado;

  const AppUser({
    required this.id,
    required this.email,
    required this.nombre,
    required this.rol,
    this.nivelEstimado,
    this.rangoEstimado,
  });

  factory AppUser.fromMap(Map<String, dynamic> map) {
    return AppUser(
      id: map['id'] as int,
      email: map['email'] as String,
      nombre: map['nombre'] as String,
      rol: (map['rol'] as String?) ?? rolJugador,
      nivelEstimado: map['nivel_estimado'] as int?,
      rangoEstimado: map['rango_estimado'] as String?,
    );
  }

  bool get esJugador => rol == rolJugador;
}

/// Estado de sesión de la app. Se crea una sola vez en `main.dart`; el router
/// lo escucha (`refreshListenable`) para decidir qué pantallas se pueden ver.
class AuthProvider extends ChangeNotifier {
  final AuthApiService _api;
  AppUser? _user;
  bool _isInitializing = true;
  bool _isLoading = false;
  String? _error;
  EstadisticasUsuario? _estadisticas;
  bool _cargandoEstadisticas = false;

  AuthProvider({AuthApiService? api}) : _api = api ?? AuthApiService() {
    _restaurarSesion();
  }

  AppUser? get user => _user;

  /// Estadísticas del jugador para la página principal — `null` si todavía no
  /// se cargaron o si el pedido falló (sin esa información la UI muestra '—').
  EstadisticasUsuario? get estadisticas => _estadisticas;

  /// `true` mientras se está pidiendo `/usuario/estadisticas`.
  bool get cargandoEstadisticas => _cargandoEstadisticas;

  /// `true` mientras se comprueba si había una sesión guardada (splash).
  bool get isInitializing => _isInitializing;

  /// `true` mientras hay un login/registro en curso (botón deshabilitado).
  bool get isLoading => _isLoading;
  bool get isLoggedIn => _user != null;
  String? get error => _error;

  Future<void> _restaurarSesion() async {
    try {
      if (await _api.hasStoredToken()) {
        final data = await _api.getCurrentUser();
        if (data != null) {
          final user = AppUser.fromMap(data);
          if (user.esJugador) {
            _user = user;
          } else {
            await _api.logout();
          }
        }
      }
    } catch (_) {
      _user = null;
    }
    _isInitializing = false;
    notifyListeners();
  }

  Future<bool> login({required String email, required String password}) {
    return _ejecutar(() => _api.login(email: email, password: password));
  }

  Future<bool> register({required String email, required String password, required String nombre}) {
    return _ejecutar(() => _api.register(email: email, password: password, nombre: nombre));
  }

  Future<bool> _ejecutar(Future<Map<String, dynamic>> Function() accion) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final user = AppUser.fromMap(await accion());
      if (!user.esJugador) {
        // El backend ya lo rechaza con 403; esto es una segunda barrera por
        // si algún día se llama sin `rol_esperado`.
        await _api.logout();
        _error = 'Esta app es solo para jugadores';
        return false;
      }
      _user = user;
      return true;
    } catch (e) {
      _error = AuthApiService.mensajeDeError(e);
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await _api.logout();
    _user = null;
    notifyListeners();
  }

  void clearError() {
    if (_error == null) return;
    _error = null;
    notifyListeners();
  }

  /// Guarda en el backend el nivel/rango que acaba de calcular "Mide tu
  /// nivel" (HU5/HU10). Si falla (sin red, token vencido) no bloquea el
  /// flujo del jugador — el resultado ya se mostró en pantalla, esto solo
  /// lo persiste para el resto de la app (ej. el perfil).
  Future<void> guardarNivelEstimado({required int nivel, required String rango}) async {
    try {
      await _api.guardarNivelEstimado(nivel: nivel, rango: rango);
    } catch (_) {
      // best-effort — ver docstring.
    }
  }

  /// Pide las estadísticas del jugador al backend. Es best-effort: si falla
  /// (sin red, token inválido) deja `_estadisticas` en `null` y la UI muestra
  /// un marcador de "sin datos" en vez de bloquear la pantalla.
  Future<void> cargarEstadisticas() async {
    _cargandoEstadisticas = true;
    notifyListeners();
    try {
      _estadisticas = await _api.estadisticasUsuario();
    } catch (_) {
      _estadisticas = null;
    } finally {
      _cargandoEstadisticas = false;
      notifyListeners();
    }
  }
}
