import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const _kUserIdKey = 'user_id';
  static const _kUserNameKey = 'user_name';
  static const _kUserEmailKey = 'user_email';
  static const _kUserPhotoKey = 'user_photo';
  static const _kIsLoggedInKey = 'is_logged_in';

  final GoogleSignIn _googleSignIn = GoogleSignIn.instance;

  Future<void> initialize() async {
    await _googleSignIn.initialize(
      serverClientId: '840567566478-qopmqu3qk27hcp0d60vkil2urcsb0l3i.apps.googleusercontent.com',
    );
  }

  Future<GoogleSignInAccount?> signInWithGoogle() async {
    try {
      final account = await _googleSignIn.authenticate(
        scopeHint: ['email', 'profile'],
      );
      if (account != null) {
        await _saveUserData(account);
        return account;
      }
      return null;
    } catch (e) {
      throw Exception('Error al iniciar sesión con Google: $e');
    }
  }

  Future<void> _saveUserData(GoogleSignInAccount account) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kUserIdKey, account.id);
    await prefs.setString(_kUserNameKey, account.displayName ?? '');
    await prefs.setString(_kUserEmailKey, account.email);
    await prefs.setString(_kUserPhotoKey, account.photoUrl ?? '');
    await prefs.setBool(_kIsLoggedInKey, true);
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kIsLoggedInKey) ?? false;
  }

  Future<Map<String, String?>> getUserData() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'id': prefs.getString(_kUserIdKey),
      'name': prefs.getString(_kUserNameKey),
      'email': prefs.getString(_kUserEmailKey),
      'photo': prefs.getString(_kUserPhotoKey),
    };
  }

  Stream<GoogleSignInAccount?> get authStateChanges => _googleSignIn.authenticationEvents
      .map((event) {
        if (event is GoogleSignInAuthenticationEventSignIn) {
          return event.user;
        }
        return null;
      });
}