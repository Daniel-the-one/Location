import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import 'models.dart';
import 'owner_api.dart';
import 'owner_property_screen.dart';
import 'property_wizard_screen.dart';

/// Onglet « Mes biens » : liste des annonces du propriétaire et accès à l'assistant.
class MyPropertiesScreen extends StatefulWidget {
  const MyPropertiesScreen({super.key});

  @override
  State<MyPropertiesScreen> createState() => _MyPropertiesScreenState();
}

class _MyPropertiesScreenState extends State<MyPropertiesScreen> {
  late Future<List<OwnerProperty>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final future = context.read<OwnerApi>().myProperties();
    setState(() {
      _future = future;
    });
  }

  Future<void> _open(Widget screen) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
    if (mounted) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _open(const PropertyWizardScreen()),
        icon: const Icon(Icons.add_home_outlined),
        label: const Text('Nouveau bien'),
      ),
      body: FutureBuilder<List<OwnerProperty>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            final msg = snap.error is ApiException ? snap.error.toString() : 'Erreur inattendue.';
            return _Message(icon: Icons.cloud_off, text: msg, action: ('Réessayer', _reload));
          }
          final items = snap.data!;
          if (items.isEmpty) {
            return const _Message(
              icon: Icons.home_work_outlined,
              text: 'Vous n\'avez pas encore de bien.\n'
                  'L\'assistant vous guide en quelques minutes, photos comprises.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async => _reload(),
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
              itemCount: items.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _PropertyTile(
                property: items[i],
                onTap: () => _open(OwnerPropertyScreen(propertyId: items[i].id)),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _PropertyTile extends StatelessWidget {
  const _PropertyTile({required this.property, required this.onTap});

  final OwnerProperty property;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = property;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.all(12),
        leading: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: SizedBox.square(
            dimension: 56,
            child: p.entrancePhoto != null
                ? Image.network(p.entrancePhoto!, fit: BoxFit.cover)
                : const ColoredBox(color: Colors.black12, child: Icon(Icons.door_front_door)),
          ),
        ),
        title: Text(p.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text('${p.neighborhood}, ${p.city} · ${formatXof(p.rent)}/mois\n'
            '${p.rooms.length} pièce(s) dans la visite'),
        isThreeLine: true,
        trailing: StatusChip(status: p.status, label: p.statusLabel),
      ),
    );
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status, required this.label});

  final String status;
  final String label;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final (bg, fg) = switch (status) {
      'published' => (scheme.primaryContainer, scheme.onPrimaryContainer),
      'rejected' || 'suspended' => (scheme.errorContainer, scheme.onErrorContainer),
      'pending' => (scheme.tertiaryContainer, scheme.onTertiaryContainer),
      _ => (scheme.surfaceContainerHighest, scheme.onSurfaceVariant),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
      child: Text(label.split(' ').first, style: TextStyle(color: fg, fontSize: 12)),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.icon, required this.text, this.action});

  final IconData icon;
  final String text;
  final (String, VoidCallback)? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 16),
            Text(text, textAlign: TextAlign.center),
            if (action != null) ...[
              const SizedBox(height: 16),
              OutlinedButton(onPressed: action!.$2, child: Text(action!.$1)),
            ],
          ],
        ),
      ),
    );
  }
}
