import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import 'auth_service.dart';
import 'user.dart';
import 'widgets.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  UserRole _role = UserRole.tenant;
  bool _busy = false;
  String? _error;
  Map<String, String> _fieldErrors = {};

  @override
  void dispose() {
    for (final c in [_firstName, _lastName, _email, _phone, _password]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
      _fieldErrors = {};
    });
    try {
      await context.read<AuthService>().register(
            email: _email.text,
            password: _password.text,
            firstName: _firstName.text,
            lastName: _lastName.text,
            phone: _phone.text,
            role: _role,
          );
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } on ApiException catch (e) {
      setState(() {
        _fieldErrors = e.fieldErrors;
        _error = e.fieldErrors.isEmpty ? e.message : null;
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  InputDecoration _decoration(String label, String field, {String? helper}) => InputDecoration(
        labelText: label,
        helperText: helper,
        errorText: _fieldErrors[field],
        border: const OutlineInputBorder(),
      );

  @override
  Widget build(BuildContext context) {
    return AuthScaffold(
      title: 'Créer un compte',
      child: Form(
        key: _form,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_error != null) ErrorBanner(_error!),
            Text('Vous êtes :', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            SegmentedButton<UserRole>(
              segments: const [
                ButtonSegment(
                  value: UserRole.tenant,
                  icon: Icon(Icons.search),
                  label: Text('Je cherche un logement'),
                ),
                ButtonSegment(
                  value: UserRole.owner,
                  icon: Icon(Icons.home_work_outlined),
                  label: Text('Je loue mon bien'),
                ),
              ],
              selected: {_role},
              onSelectionChanged: (s) => setState(() => _role = s.first),
            ),
            if (_role == UserRole.owner)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Après l\'inscription, vous téléverserez une pièce d\'identité. '
                  'Vos annonces seront publiées une fois votre identité validée.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _firstName,
                    decoration: _decoration('Prénom', 'first_name'),
                    validator: requiredField,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _lastName,
                    decoration: _decoration('Nom', 'last_name'),
                    validator: requiredField,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: _decoration('Email', 'email'),
              validator: emailField,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              decoration: _decoration('Téléphone (WhatsApp)', 'phone', helper: 'Ex. +228 90 00 00 00'),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _password,
              obscureText: true,
              decoration: _decoration('Mot de passe', 'password', helper: '8 caractères minimum'),
              validator: (v) => (v == null || v.length < 8) ? '8 caractères minimum' : null,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: _busy
                  ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Créer mon compte'),
            ),
          ],
        ),
      ),
    );
  }
}
