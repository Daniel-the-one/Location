/// Adresse de l'API. À fixer au build :
///   flutter run -d chrome --dart-define=API_URL=http://127.0.0.1:8000/api
///   `flutter build web --dart-define=API_URL=https://NOM-DU-BACKEND.onrender.com/api`
/// Sur l'émulateur Android, la machine hôte est 10.0.2.2.
const String apiBaseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://127.0.0.1:8000/api',
);
