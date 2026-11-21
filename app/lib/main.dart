import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'features/auth/auth_service.dart';
import 'features/auth/login_screen.dart';
import 'features/home/home_screen.dart';

void main() {
  final auth = AuthService(ApiClient())..restore();
  runApp(ChangeNotifierProvider.value(value: auth, child: const EssiviviApp()));
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
