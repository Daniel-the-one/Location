import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../auth/widgets.dart';
import 'models.dart';
import 'my_properties_screen.dart' show StatusChip;
import 'owner_api.dart';
import 'photo_picker.dart';
import 'room_photos_screen.dart';

/// Fiche d'un bien côté propriétaire : porte d'entrée, pièces et photos, soumission.
class OwnerPropertyScreen extends StatefulWidget {
  const OwnerPropertyScreen({super.key, required this.propertyId});

  final int propertyId;

  @override
  State<OwnerPropertyScreen> createState() => _OwnerPropertyScreenState();
}

class _OwnerPropertyScreenState extends State<OwnerPropertyScreen> {
  OwnerProperty? _p;
  bool _busy = false;
  String? _error;

  OwnerApi get _api => context.read<OwnerApi>();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() => _guard(() async {
        final p = await _api.property(widget.propertyId);
        setState(() => _p = p);
      });

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

  Future<void> _entrance({required bool camera}) async {
    final picker = context.read<PhotoPicker>();
    final file = camera ? await picker.takePhoto('image') : await picker.pickOne('image');
    if (file == null) return;
    await _guard(() async {
      final p = await _api.uploadEntrance(widget.propertyId, file);
      setState(() => _p = p);
    });
  }

  Future<void> _action(String name, String done) => _guard(() async {
        final p = await _api.action(widget.propertyId, name);
        setState(() => _p = p);
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
      });

  Future<void> _openRoom(Room room) async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => RoomPhotosScreen(room: room)),
    );
    if (mounted) _load();
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    return Scaffold(
      appBar: AppBar(title: Text(p?.title ?? 'Mon bien')),
      body: p == null
          ? Center(
              child: _error != null
                  ? Padding(padding: const EdgeInsets.all(16), child: ErrorBanner(_error!))
                  : const CircularProgressIndicator(),
            )
          : RefreshIndicator(
              onRefresh: _load,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 720),
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (_error != null) ErrorBanner(_error!),
                      _statusCard(p),
                      const SizedBox(height: 16),
                      _entranceCard(p),
                      const SizedBox(height: 16),
                      Text('Pièces de la visite', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      for (final (i, room) in p.rooms.indexed) _roomTile(i, room, p),
                      const SizedBox(height: 24),
                      ..._actions(p),
                    ],
                  ),
                ),
              ),
            ),
    );
  }

  Widget _statusCard(OwnerProperty p) {
    final hint = switch (p.status) {
      'draft' => 'Ajoutez la photo de la porte et les photos de chaque pièce, puis soumettez.',
      'pending' => 'L\'administrateur vérifie votre annonce. Vous serez prévenu par email.',
      'published' => 'Votre annonce est visible par les locataires.',
      'rejected' => 'Motif : ${p.rejectionReason}. Corrigez puis soumettez à nouveau.',
      'suspended' => p.suspendedByAdmin
          ? 'Suspendue par l\'administrateur. ${p.rejectionReason}'
          : 'Vous avez suspendu l\'annonce : elle n\'est plus visible.',
      _ => '',
    };
    return Card(
      child: ListTile(
        title: Text('${propertyTypes[p.propertyType]} · ${p.neighborhood}, ${p.city}'),
        subtitle: Text('${formatXof(p.rent)} / mois\n$hint'),
        isThreeLine: true,
        trailing: StatusChip(status: p.status, label: p.statusLabel),
      ),
    );
  }

  Widget _entranceCard(OwnerProperty p) => Card(
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AspectRatio(
              aspectRatio: 16 / 9,
              child: p.entrancePhoto != null
                  ? Image.network(p.entrancePhoto!, fit: BoxFit.cover)
                  : ColoredBox(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      child: const Center(child: Icon(Icons.door_front_door_outlined, size: 48)),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Porte d\'entrée'),
                  const Text(
                    'C\'est la première image de la visite : photographiez la porte de face, '
                    'bien éclairée.',
                    style: TextStyle(fontSize: 12),
                  ),
                  const SizedBox(height: 8),
                  Wrap(spacing: 8, children: [
                    FilledButton.tonalIcon(
                      onPressed: _busy || p.status == 'pending' ? null : () => _entrance(camera: true),
                      icon: const Icon(Icons.photo_camera_outlined),
                      label: Text(p.entrancePhoto == null ? 'Photographier' : 'Reprendre'),
                    ),
                    TextButton(
                      onPressed: _busy || p.status == 'pending' ? null : () => _entrance(camera: false),
                      child: const Text('Depuis la galerie'),
                    ),
                  ]),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _roomTile(int i, Room room, OwnerProperty p) {
    final done = room.photosCount > 0;
    return Card(
      child: ListTile(
        leading: CircleAvatar(child: Text('${i + 1}')),
        title: Text(room.name),
        subtitle: Text(done ? '${room.photosCount} photo(s)' : 'Pas encore de photo'),
        trailing: Icon(done ? Icons.check_circle : Icons.add_a_photo_outlined,
            color: done ? Theme.of(context).colorScheme.primary : null),
        onTap: p.status == 'pending' ? null : () => _openRoom(room),
      ),
    );
  }

  List<Widget> _actions(OwnerProperty p) => [
        if (p.status == 'draft' || p.status == 'rejected')
          FilledButton.icon(
            onPressed: _busy ? null : () => _action('submit', 'Annonce envoyée pour validation.'),
            icon: const Icon(Icons.send),
            label: const Text('Soumettre à l\'administrateur'),
          ),
        if (p.status == 'published')
          OutlinedButton.icon(
            onPressed: _busy ? null : () => _action('suspend', 'Annonce suspendue.'),
            icon: const Icon(Icons.pause_circle_outline),
            label: const Text('Suspendre l\'annonce'),
          ),
        if (p.status == 'suspended' && !p.suspendedByAdmin)
          FilledButton.icon(
            onPressed: _busy ? null : () => _action('reactivate', 'Annonce de nouveau visible.'),
            icon: const Icon(Icons.play_circle_outline),
            label: const Text('Réactiver l\'annonce'),
          ),
      ];
}
