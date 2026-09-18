import 'package:flutter/material.dart';
import 'local_auth_service.dart';

class AppUser {
  final String email;
  final String name;

  const AppUser({required this.email, required this.name});

  factory AppUser.fromMap(Map<String, String?> map) {
    return AppUser(
      email: map['email'] ?? '',
      name: map['name'] ?? '',
    );
  }
}

class LocalAuthProvider extends ChangeNotifier {
  final LocalAuthService _authService = LocalAuthService();
  AppUser? _user;
  bool _isLoading = false;
  String? _error;

  AppUser? get user => _user;
  bool get isLoading => _isLoading;
  bool get isLoggedIn => _user != null;
  String? get error => _error;

  LocalAuthProvider() {
    _checkAuthState();
  }

  Future<void> _checkAuthState() async {
    _isLoading = true;
    notifyListeners();

    await _authService.initialize();
    final loggedIn = await _authService.isLoggedIn();
    if (loggedIn) {
      final userData = await _authService.getCurrentUser();
      if (userData.isNotEmpty) {
        _user = AppUser.fromMap(userData);
      }
    }
    _isLoading = false;
    notifyListeners();
  }

  Future<bool> login({
    required String email,
    required String password,
    bool rememberMe = false,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final success = await _authService.login(
        email: email,
        password: password,
        rememberMe: rememberMe,
      );
      if (success) {
        final userData = await _authService.getCurrentUser();
        _user = AppUser.fromMap(userData);
      } else {
        _error = 'Email o contraseña incorrectos';
      }
      _isLoading = false;
      notifyListeners();
      return success;
    } catch (e) {
      _error = 'Error al iniciar sesión: $e';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> register({
    required String email,
    required String password,
    required String name,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final success = await _authService.register(
        email: email,
        password: password,
        name: name,
      );
      if (success) {
        await _authService.login(email: email, password: password);
        final userData = await _authService.getCurrentUser();
        _user = AppUser.fromMap(userData);
      } else {
        _error = 'El email ya está registrado';
      }
      _isLoading = false;
      notifyListeners();
      return success;
    } catch (e) {
      _error = 'Error al registrarse: $e';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    _user = null;
    notifyListeners();
  }

  Future<bool> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    if (_user == null) return false;

    final success = await _authService.changePassword(
      email: _user!.email,
      currentPassword: currentPassword,
      newPassword: newPassword,
    );
    return success;
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}