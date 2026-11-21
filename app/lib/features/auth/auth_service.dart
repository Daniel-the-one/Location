import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/api_client.dart';
import 'user.dart';

/// État de connexion partagé dans toute l'application.
class AuthService extends ChangeNotifier {
  AuthService(this.api);

  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';

  final ApiClient api;
  AppUser? user;
  bool restoring = true;

  bool get isLoggedIn => user != null;

  /// Au démarrage : reprend la session enregistrée si les jetons sont encore valides.
  Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    final access = prefs.getString(_accessKey);
    final refresh = prefs.getString(_refreshKey);
    try {
      if (access != null) {
        api.accessToken = access;
        try {
          user = AppUser.fromJson(await api.get('/auth/me/'));
        } on ApiException catch (e) {
          if (e.statusCode != 401 || refresh == null) rethrow;
          final res = await api.post('/auth/refresh/', {'refresh': refresh});
          await _saveTokens(res['access'] as String, refresh);
          user = AppUser.fromJson(await api.get('/auth/me/'));
        }
      }
    } on ApiException {
      await _clear();
    }
    restoring = false;
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    final res = await api.post('/auth/login/', {'email': email.trim(), 'password': password});
    await _openSession(res);
  }

  Future<void> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    required String phone,
    required UserRole role,
  }) async {
    final res = await api.post('/auth/register/', {
      'email': email.trim(),
      'password': password,
      'first_name': firstName.trim(),
      'last_name': lastName.trim(),
      'phone': phone.trim(),
      'role': role.name,
    });
    await _openSession(res);
  }

  Future<void> requestPasswordReset(String email) =>
      api.post('/auth/password-reset/', {'email': email.trim()});

  Future<void> logout() async {
    await _clear();
    notifyListeners();
  }

  Future<void> _openSession(Map<String, dynamic> res) async {
    await _saveTokens(res['access'] as String, res['refresh'] as String);
    user = AppUser.fromJson(res['user'] as Map<String, dynamic>);
    notifyListeners();
  }

  Future<void> _saveTokens(String access, String refresh) async {
    api.accessToken = access;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_accessKey, access);
    await prefs.setString(_refreshKey, refresh);
  }

  Future<void> _clear() async {
    api.accessToken = null;
    user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_accessKey);
    await prefs.remove(_refreshKey);
  }
}
