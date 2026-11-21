import 'dart:typed_data';

import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../auth/widgets.dart';
import 'models.dart';
import 'owner_api.dart';
import 'photo_picker.dart';
import 'shooting_guide.dart';

const _target = 12;
const _minimum = 8;

/// Photos d'une pièce : guide, prise de vue une par une ou depuis la galerie, envoi.
class RoomPhotosScreen extends StatefulWidget {
  const RoomPhotosScreen({super.key, required this.room});

  final Room room;

  @override
  State<RoomPhotosScreen> createState() => _RoomPhotosScreenState();
}

class _RoomPhotosScreenState extends State<RoomPhotosScreen> {
  final List<UploadFile> _pending = [];
  late int _uploaded = widget.room.photosCount;
  bool _busy = false;
  String? _error;

  int get _total => _uploaded + _pending.length;

  Future<void> _take() async {
    final photo = await context.read<PhotoPicker>().takePhoto('images');
    if (photo != null) setState(() => _pending.add(photo));
  }

  Future<void> _gallery() async {
    final photos = await context.read<PhotoPicker>().pickMany('images');
    setState(() => _pending.addAll(photos));
  }

  Future<void> _guard(Future<void> Function() task) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await task();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send() => _guard(() async {
        await context.read<OwnerApi>().uploadRoomPhotos(widget.room.id, _pending);
        setState(() {
          _uploaded += _pending.length;
          _pending.clear();
        });
        if (mounted) {
          ScaffoldMessenger.of(context)
              .showSnackBar(const SnackBar(content: Text('Photos envoyées.')));
        }
      });

  Future<void> _clearUploaded() => _guard(() async {
        await context.read<OwnerApi>().clearRoomPhotos(widget.room.id);
        setState(() => _uploaded = 0);
      });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final progress = (_total / _target).clamp(0.0, 1.0);
    return Scaffold(
      appBar: AppBar(title: Text(widget.room.name)),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (_error != null) ErrorBanner(_error!),
              const ShootingGuide(),
              const SizedBox(height: 16),
              Text('$_total / $_target photos', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              LinearProgressIndicator(value: progress, minHeight: 8),
              const SizedBox(height: 4),
              Text(
                _total < _minimum
                    ? 'Encore ${_minimum - _total} photo(s) au minimum pour assembler le panorama.'
                    : 'Assez de photos pour le panorama.',
                style: theme.textTheme.bodySmall,
              ),
              if (_uploaded > 0) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Icon(Icons.cloud_done_outlined, color: theme.colorScheme.primary),
                    const SizedBox(width: 8),
                    Expanded(child: Text('$_uploaded photo(s) déjà envoyée(s)')),
                    TextButton(
                      onPressed: _busy ? null : _clearUploaded,
                      child: const Text('Tout refaire'),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 16),
              if (_pending.isNotEmpty)
                GridView.count(
                  crossAxisCount: 4,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 4,
                  crossAxisSpacing: 4,
                  children: [
                    for (final (i, p) in _pending.indexed)
                      Stack(
                        fit: StackFit.expand,
                        children: [
                          Image.memory(Uint8List.fromList(p.bytes), fit: BoxFit.cover),
                          Positioned(
                            right: 0,
                            top: 0,
                            child: IconButton.filledTonal(
                              tooltip: 'Retirer',
                              iconSize: 16,
                              onPressed: () => setState(() => _pending.removeAt(i)),
                              icon: const Icon(Icons.close),
                            ),
                          ),
                        ],
                      ),
                  ],
                ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.tonalIcon(
                      onPressed: _busy || _total >= 16 ? null : _take,
                      icon: const Icon(Icons.photo_camera_outlined),
                      label: const Text('Prendre une photo'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _busy || _total >= 16 ? null : _gallery,
                      icon: const Icon(Icons.photo_library_outlined),
                      label: const Text('Galerie'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _busy || _pending.isEmpty ? null : _send,
                child: _busy
                    ? const SizedBox.square(
                        dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : Text(_pending.isEmpty
                        ? 'Aucune nouvelle photo à envoyer'
                        : 'Envoyer ${_pending.length} photo(s)'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
