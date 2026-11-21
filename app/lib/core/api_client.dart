import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';

/// Erreur renvoyée par l'API, avec un message lisible pour l'utilisateur.
class ApiException implements Exception {
  ApiException(this.statusCode, this.message, [this.fieldErrors = const {}]);

  final int statusCode;
  final String message;
  final Map<String, String> fieldErrors;

  @override
  String toString() => message;
}

/// Un fichier à téléverser : nom du champ attendu par l'API, octets, nom de fichier.
class UploadFile {
  const UploadFile(this.field, this.bytes, this.filename);

  final String field;
  final List<int> bytes;
  final String filename;
}

/// Client HTTP JSON. Ajoute le jeton d'accès quand il est connu.
class ApiClient {
  ApiClient({http.Client? httpClient, this.baseUrl = apiBaseUrl})
      : _http = httpClient ?? http.Client();

  final http.Client _http;
  final String baseUrl;
  String? accessToken;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (accessToken != null) 'Authorization': 'Bearer $accessToken',
      };

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<Map<String, dynamic>> get(String path) async =>
      _decode(await _send(() => _http.get(_uri(path), headers: _headers)));

  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async =>
      _decode(await _send(
          () => _http.post(_uri(path), headers: _headers, body: jsonEncode(body))));

  Future<Map<String, dynamic>> patch(String path, Map<String, dynamic> body) async =>
      _decode(await _send(
          () => _http.patch(_uri(path), headers: _headers, body: jsonEncode(body))));

  Future<Map<String, dynamic>> delete(String path) async =>
      _decode(await _send(() => _http.delete(_uri(path), headers: _headers)));

  /// Envoi multipart (photos, pièce d'identité). Fonctionne sur le web comme sur Android
  /// car les fichiers sont passés en octets.
  Future<Map<String, dynamic>> upload(
    String path,
    List<UploadFile> files, {
    Map<String, String> fields = const {},
  }) async {
    final request = http.MultipartRequest('POST', _uri(path))
      ..headers.addAll({
        'Accept': 'application/json',
        if (accessToken != null) 'Authorization': 'Bearer $accessToken',
      })
      ..fields.addAll(fields);
    for (final f in files) {
      request.files.add(http.MultipartFile.fromBytes(f.field, f.bytes, filename: f.filename));
    }
    return _decode(await _send(() async => http.Response.fromStream(await _http.send(request))));
  }

  Future<http.Response> _send(Future<http.Response> Function() call) async {
    try {
      return await call();
    } on Exception {
      throw ApiException(0, 'Impossible de joindre le serveur. Vérifiez votre connexion.');
    }
  }

  Map<String, dynamic> _decode(http.Response res) {
    final text = utf8.decode(res.bodyBytes);
    final dynamic body = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return body is Map<String, dynamic> ? body : {'results': body};
    }
    throw _toException(res.statusCode, body);
  }

  static ApiException _toException(int status, dynamic body) {
    if (body is! Map) return ApiException(status, 'Erreur serveur ($status).');
    final fields = <String, String>{};
    String? detail;
    if (body['errors'] is List) {
      // Règles métier : toutes les raisons, une par ligne.
      return ApiException(status, (body['errors'] as List).join('\n'));
    }
    body.forEach((key, value) {
      final msg = value is List ? value.join(' ') : value.toString();
      if (key == 'detail' || key == 'non_field_errors') {
        detail = msg;
      } else {
        fields[key.toString()] = msg;
      }
    });
    final message = detail ?? (fields.isNotEmpty ? fields.values.first : 'Erreur ($status).');
    return ApiException(status, message, fields);
  }
}
