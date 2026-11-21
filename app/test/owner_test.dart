import 'dart:convert';

import 'package:essivivi/core/api_client.dart';
import 'package:essivivi/features/auth/auth_service.dart';
import 'package:essivivi/features/owner/models.dart';
import 'package:essivivi/features/owner/my_properties_screen.dart';
import 'package:essivivi/features/owner/owner_api.dart';
import 'package:essivivi/main.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:material_ui/material_ui.dart';

http.Response _json(Object body, [int status = 200]) => http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _property({String status = 'draft', List rooms = const []}) => {
      'id': 7,
      'property_type': 'apartment',
      'title': 'Appartement à Bè',
      'neighborhood': 'Bè',
      'city': 'Lomé',
      'rent': 75000,
      'status': status,
      'rejection_reason': '',
      'suspended_by_admin': false,
      'entrance_photo': null,
      'rooms': rooms,
    };

void main() {
  group('RoomPlanAnswers', () {
    test('WC « dans la douche » devient « aucun » quand il n\'y a pas de douche', () {
      final a = RoomPlanAnswers()..bathroom = 'none';
      expect(a.toJson()['toilet'], 'none');
    });

    test('valeurs par défaut cohérentes avec l\'API', () {
      expect(RoomPlanAnswers().toJson(), {
        'bedrooms': 1,
        'living_room': true,
        'kitchen': 'interior',
        'bathroom': 'interior',
        'toilet': 'with_bathroom',
        'balcony': false,
        'terrace': false,
        'yard': false,
        'others': <String>[],
      });
    });
  });

  test('formatXof sépare les milliers', () {
    expect(formatXof(75000), '75 000 FCFA');
    expect(formatXof(1500000), '1 500 000 FCFA');
    expect(formatXof(500), '500 FCFA');
  });

  test('les erreurs de soumission sont toutes remontées', () async {
    final api = OwnerApi(ApiClient(
      httpClient: MockClient((_) async => _json({
            'detail': 'Ajoutez la photo de la porte d\'entrée.',
            'errors': ['Ajoutez la photo de la porte d\'entrée.', 'Pièces sans photos : Salon.'],
          }, 400)),
    ));
    expect(
      () => api.action(7, 'submit'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('Salon'))),
    );
  });

  testWidgets('Mes biens : liste avec statut, ou message si vide', (tester) async {
    var empty = false;
    final client = MockClient((req) async {
      expect(req.url.path, endsWith('/owner/properties/'));
      return _json({
        'results': empty
            ? []
            : [
                _property(status: 'published', rooms: [
                  {'id': 1, 'room_type': 'living_room', 'name': 'Salon', 'photos_count': 12},
                ]),
              ],
      });
    });
    final auth = AuthService(ApiClient(httpClient: client))..restoring = false;

    await tester.pumpWidget(AppProviders(
      auth: auth,
      child: const MaterialApp(home: MyPropertiesScreen()),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Appartement à Bè'), findsOneWidget);
    expect(find.text('Publiée'), findsOneWidget);
    expect(find.textContaining('1 pièce(s)'), findsOneWidget);

    empty = true;
    await tester.pumpWidget(AppProviders(
      auth: auth,
      child: const MaterialApp(home: MyPropertiesScreen(key: ValueKey('vide'))),
    ));
    await tester.pumpAndSettle();
    expect(find.textContaining('pas encore de bien'), findsOneWidget);
  });
}
