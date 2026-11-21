import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../auth/auth_service.dart';
import '../auth/widgets.dart';
import 'owner_api.dart';
import 'photo_picker.dart';

/// Vérification d'identité du propriétaire : envoi de la pièce et suivi du statut.
class IdentityScreen extends StatefulWidget {
  const IdentityScreen({super.key});

  @override
  State<IdentityScreen> createState() => _IdentityScreenState();
}

class _IdentityScreenState extends State<IdentityScreen> {
  Map<String, dynamic>? _latest;
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final latest = await context.read<OwnerApi>().latestIdentity();
      if (!mounted) return;
      setState(() => _latest = latest);
      if (latest?['status'] == 'approved') await context.read<AuthService>().refreshUser();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _send({required bool camera}) async {
    final picker = context.read<PhotoPicker>();
    final api = context.read<OwnerApi>();
    final file = camera ? await picker.takePhoto('document') : await picker.pickOne('document');
    if (file == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await api.uploadIdentity(file);
      await _load();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final status = _latest?['status'] as String?;
    final canUpload = status == null || status == 'rejected';
    final (icon, title, text) = switch (status) {
      'pending' => (Icons.hourglass_top, 'En cours de vérification',
          'L\'administrateur examine votre pièce. Vous serez prévenu par email.'),
      'approved' => (Icons.verified_outlined, 'Identité validée',
          'Vous pouvez soumettre vos annonces.'),
      'rejected' => (Icons.error_outline, 'Pièce refusée',
          'Motif : ${_latest?['rejection_reason'] ?? ''}\nEnvoyez une nouvelle photo.'),
      _ => (Icons.badge_outlined, 'Vérifiez votre identité',
          'Pour protéger les locataires, chaque propriétaire envoie une photo de sa carte '
              'd\'identité, de son passeport ou de son permis. Seul l\'administrateur la voit.'),
    };
    return Scaffold(
      appBar: AppBar(title: const Text('Vérification d\'identité')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_error != null) ErrorBanner(_error!),
                Icon(icon, size: 56, color: Theme.of(context).colorScheme.primary),
                const SizedBox(height: 12),
                Text(title,
                    textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text(text, textAlign: TextAlign.center),
                if (canUpload) ...[
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    onPressed: _busy ? null : () => _send(camera: true),
                    icon: const Icon(Icons.photo_camera_outlined),
                    label: const Text('Photographier ma pièce'),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: _busy ? null : () => _send(camera: false),
                    child: const Text('Choisir une image'),
                  ),
                ],
              ],
            ),
    );
  }
}
