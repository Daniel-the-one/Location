import '../../core/api_client.dart';
import 'models.dart';

/// Appels de l'API propriétaire (/api/owner/...).
class OwnerApi {
  OwnerApi(this.api);

  final ApiClient api;

  Future<List<OwnerProperty>> myProperties() async {
    final res = await api.get('/owner/properties/');
    final list = (res['results'] ?? const []) as List;
    return [for (final p in list) OwnerProperty.fromJson(p as Map<String, dynamic>)];
  }

  Future<OwnerProperty> property(int id) async =>
      OwnerProperty.fromJson(await api.get('/owner/properties/$id/'));

  Future<OwnerProperty> create(Map<String, dynamic> data) async =>
      OwnerProperty.fromJson(await api.post('/owner/properties/', data));

  Future<OwnerProperty> applyRoomPlan(int id, RoomPlanAnswers answers) async =>
      OwnerProperty.fromJson(await api.post('/owner/properties/$id/room-plan/', answers.toJson()));

  Future<OwnerProperty> reorderRooms(int id, List<int> roomIds) async => OwnerProperty.fromJson(
      await api.post('/owner/properties/$id/reorder-rooms/', {'room_ids': roomIds}));

  Future<OwnerProperty> uploadEntrance(int id, UploadFile file) async =>
      OwnerProperty.fromJson(await api.upload('/owner/properties/$id/entrance-photo/', [file]));

  Future<void> uploadRoomPhotos(int roomId, List<UploadFile> files) =>
      api.upload('/owner/rooms/$roomId/photos/', files);

  Future<void> clearRoomPhotos(int roomId) => api.delete('/owner/rooms/$roomId/photos/');

  Future<OwnerProperty> action(int id, String name) async =>
      OwnerProperty.fromJson(await api.post('/owner/properties/$id/$name/', {}));

  Future<void> uploadIdentity(UploadFile file) => api.upload('/auth/identity/', [file]);

  /// Dernière demande de vérification d'identité, ou null s'il n'y en a pas.
  Future<Map<String, dynamic>?> latestIdentity() async {
    final res = await api.get('/auth/identity/');
    final list = (res['results'] ?? const []) as List;
    return list.isEmpty ? null : list.first as Map<String, dynamic>;
  }
}
