import 'dart:convert';

import 'package:essivivi/core/api_client.dart';
import 'package:essivivi/features/auth/auth_service.dart';
import 'package:essivivi/main.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _userJson = {
  'id': 1,
  'email': 'kofi@example.com',
  'first_name': 'Kofi',
  'last_name': 'Mensah',
  'phone': '',
  'role': 'owner',
  'is_identity_verified': false,
};

Widget _app(AuthService auth) => AppProviders(auth: auth, child: const EssiviviApp());

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('sans session, affiche la connexion', (tester) async {
    final auth = AuthService(ApiClient(httpClient: MockClient((_) async => http.Response('', 500))));
    await auth.restore();
    await tester.pumpWidget(_app(auth));
    expect(find.text('Connexion'), findsOneWidget);
    expect(find.text('Créer un compte'), findsOneWidget);
  });

  testWidgets('connexion réussie : accueil propriétaire', (tester) async {
    final client = MockClient((req) async {
      // Après connexion, l'accueil propriétaire charge la liste de ses biens.
      final body = req.url.path.endsWith('/owner/properties/')
          ? {'results': []}
          : {'access': 'a', 'refresh': 'r', 'user': _userJson};
      expect(req.url.path, anyOf(endsWith('/auth/login/'), endsWith('/owner/properties/')));
      return http.Response(jsonEncode(body), 200, headers: {'content-type': 'application/json'});
    });
    final auth = AuthService(ApiClient(httpClient: client));
    await auth.restore();
    await tester.pumpWidget(_app(auth));

    await tester.enterText(find.byType(TextFormField).at(0), 'kofi@example.com');
    await tester.enterText(find.byType(TextFormField).at(1), 'Lome-2026-secure');
    await tester.tap(find.text('Se connecter'));
    await tester.pumpAndSettle();

    expect(find.text('Mes biens'), findsWidgets);
    expect(auth.api.accessToken, 'a');
  });

  testWidgets('mauvais mot de passe : message clair', (tester) async {
    final client = MockClient(
      (_) async => http.Response(jsonEncode({'detail': 'No active account'}), 401),
    );
    final auth = AuthService(ApiClient(httpClient: client));
    await auth.restore();
    await tester.pumpWidget(_app(auth));

    await tester.enterText(find.byType(TextFormField).at(0), 'kofi@example.com');
    await tester.enterText(find.byType(TextFormField).at(1), 'faux');
    await tester.tap(find.text('Se connecter'));
    await tester.pumpAndSettle();

    expect(find.text('Email ou mot de passe incorrect.'), findsOneWidget);
  });
}
