import 'package:image_picker/image_picker.dart';

import '../../core/api_client.dart';

/// Prise de photo ou choix en galerie, converti en fichiers prêts à téléverser.
/// Sur le web, l'appareil photo passe par le sélecteur de fichiers du navigateur.
class PhotoPicker {
  PhotoPicker([ImagePicker? picker]) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  Future<UploadFile?> takePhoto(String field) async {
    final file = await _picker.pickImage(source: ImageSource.camera, maxWidth: 2400);
    return file == null ? null : _toUpload(field, file);
  }

  Future<UploadFile?> pickOne(String field) async {
    final file = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 2400);
    return file == null ? null : _toUpload(field, file);
  }

  Future<List<UploadFile>> pickMany(String field) async {
    final files = await _picker.pickMultiImage(maxWidth: 2400);
    return [for (final f in files) await _toUpload(field, f)];
  }

  static Future<UploadFile> _toUpload(String field, XFile f) async =>
      UploadFile(field, await f.readAsBytes(), f.name.isEmpty ? 'photo.jpg' : f.name);
}
