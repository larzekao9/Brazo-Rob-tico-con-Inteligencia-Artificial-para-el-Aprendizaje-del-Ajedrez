import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:crypto/crypto.dart';

class LocalAuthService {
  static const _kUsersKey = 'local_users';
  static const _kCurrentUserKey = 'current_user_email';
  static const _kRememberMeKey = 'remember_me';

  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    if (!prefs.containsKey(_kUsersKey)) {
      await prefs.setString(_kUsersKey, '{}');
    }
  }

  String _hashPassword(String password) {
    final bytes = utf8.encode(password);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  Future<bool> register({
    required String email,
    required String password,
    required String name,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final usersJson = prefs.getString(_kUsersKey) ?? '{}';
    final Map<String, dynamic> users = jsonDecode(usersJson);

    if (users.containsKey(email)) {
      return false; // Usuario ya existe
    }

    users[email] = {
      'name': name,
      'passwordHash': _hashPassword(password),
      'createdAt': DateTime.now().toIso8601String(),
    };

    await prefs.setString(_kUsersKey, jsonEncode(users));
    return true;
  }

  Future<bool> login({
    required String email,
    required String password,
    bool rememberMe = false,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final usersJson = prefs.getString(_kUsersKey) ?? '{}';
    final Map<String, dynamic> users = jsonDecode(usersJson);

    if (!users.containsKey(email)) {
      return false;
    }

    final user = users[email];
    final passwordHash = _hashPassword(password);

    if (user['passwordHash'] != passwordHash) {
      return false;
    }

    await prefs.setString(_kCurrentUserKey, email);
    if (rememberMe) {
      await prefs.setBool(_kRememberMeKey, true);
    }

    return true;
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kCurrentUserKey);
  }

  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.containsKey(_kCurrentUserKey);
  }

  Future<Map<String, String?>> getCurrentUser() async {
    final prefs = await SharedPreferences.getInstance();
    final email = prefs.getString(_kCurrentUserKey);
    if (email == null) return {};

    final usersJson = prefs.getString(_kUsersKey) ?? '{}';
    final Map<String, dynamic> users = jsonDecode(usersJson);
    final user = users[email];

    if (user == null) return {};

    return {
      'email': email,
      'name': user['name'],
    };
  }

  Future<bool> changePassword({
    required String email,
    required String currentPassword,
    required String newPassword,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final usersJson = prefs.getString(_kUsersKey) ?? '{}';
    final Map<String, dynamic> users = jsonDecode(usersJson);

    if (!users.containsKey(email)) return false;

    final user = users[email];
    if (user['passwordHash'] != _hashPassword(currentPassword)) {
      return false;
    }

    users[email]['passwordHash'] = _hashPassword(newPassword);
    await prefs.setString(_kUsersKey, jsonEncode(users));
    return true;
  }

  Future<void> deleteAccount(String email) async {
    final prefs = await SharedPreferences.getInstance();
    final usersJson = prefs.getString(_kUsersKey) ?? '{}';
    final Map<String, dynamic> users = jsonDecode(usersJson);

    users.remove(email);
    await prefs.setString(_kUsersKey, jsonEncode(users));

    final currentEmail = prefs.getString(_kCurrentUserKey);
    if (currentEmail == email) {
      await prefs.remove(_kCurrentUserKey);
    }
  }

  Future<bool> isRememberMe() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kRememberMeKey) ?? false;
  }
}