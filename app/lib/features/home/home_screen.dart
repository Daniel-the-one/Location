import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import '../auth/auth_service.dart';
import '../auth/user.dart';
import '../owner/identity_screen.dart';
import '../owner/my_properties_screen.dart';

/// Accueil après connexion : les onglets changent selon le rôle du compte.
/// Les écrans réels (annonces, assistant, messagerie…) remplaceront les placeholders.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _Tab {
  const _Tab(this.label, this.icon);
  final String label;
  final IconData icon;
}

const _tenantTabs = [
  _Tab('Annonces', Icons.search),
  _Tab('Favoris', Icons.favorite_border),
  _Tab('Messages', Icons.chat_bubble_outline),
  _Tab('Profil', Icons.person_outline),
];

const _ownerTabs = [
  _Tab('Mes biens', Icons.home_work_outlined),
  _Tab('Demandes', Icons.inbox_outlined),
  _Tab('Messages', Icons.chat_bubble_outline),
  _Tab('Profil', Icons.person_outline),
];

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final user = auth.user!;
    final tabs = user.role == UserRole.owner ? _ownerTabs : _tenantTabs;
    final tab = tabs[_index];

    return Scaffold(
      appBar: AppBar(title: Text(tab.label)),
      body: switch (tab.label) {
        'Profil' => _ProfileTab(user: user, onLogout: auth.logout),
        'Mes biens' => const MyPropertiesScreen(),
        _ => Center(child: Text('${tab.label} — à venir')),
      },
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          for (final t in tabs) NavigationDestination(icon: Icon(t.icon), label: t.label),
        ],
      ),
    );
  }
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab({required this.user, required this.onLogout});

  final AppUser user;
  final Future<void> Function() onLogout;

  @override
  Widget build(BuildContext context) {
    final roleLabel = switch (user.role) {
      UserRole.tenant => 'Locataire',
      UserRole.owner => 'Propriétaire',
      UserRole.admin => 'Administrateur',
    };
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        ListTile(
          leading: const CircleAvatar(child: Icon(Icons.person)),
          title: Text(user.fullName),
          subtitle: Text('${user.email}\n$roleLabel'),
          isThreeLine: true,
        ),
        if (user.role == UserRole.owner && !user.isIdentityVerified)
          Card(
            child: ListTile(
              leading: const Icon(Icons.badge_outlined),
              title: const Text('Identité non vérifiée'),
              subtitle: const Text('Envoyez une pièce d\'identité pour pouvoir publier vos annonces.'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const IdentityScreen()),
              ),
            ),
          ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: onLogout,
          icon: const Icon(Icons.logout),
          label: const Text('Se déconnecter'),
        ),
      ],
    );
  }
}
