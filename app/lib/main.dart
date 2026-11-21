import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'features/auth/auth_service.dart';
import 'features/auth/login_screen.dart';
import 'features/home/home_screen.dart';
import 'features/owner/owner_api.dart';
import 'features/owner/photo_picker.dart';

void main() {
  final api = ApiClient();
  final auth = AuthService(api)..restore();
  runApp(AppProviders(auth: auth, child: const EssiviviApp()));
}

/// Services partagés. Les tests passent leurs propres instances (client HTTP simulé…).
class AppProviders extends StatelessWidget {
  const AppProviders({super.key, required this.auth, required this.child, this.picker});

  final AuthService auth;
  final PhotoPicker? picker;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: auth),
        Provider(create: (_) => OwnerApi(auth.api)),
        Provider(create: (_) => picker ?? PhotoPicker()),
      ],
      child: child,
    );
  }
}

class EssiviviApp extends StatelessWidget {
  const EssiviviApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Essivivi',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1F6F5C)),
      ),
      home: const AuthGate(),
    );
  }
}

/// Affiche l'écran de connexion ou l'accueil selon l'état de la session.
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    if (auth.restoring) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return auth.isLoggedIn ? const HomeScreen() : const LoginScreen();
  }
}
