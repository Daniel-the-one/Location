import 'package:material_ui/material_ui.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../auth/widgets.dart';
import 'models.dart';
import 'owner_api.dart';
import 'owner_property_screen.dart';

/// Assistant de création d'un bien en 4 étapes :
/// 1. type et description, 2. adresse et prix (création du brouillon),
/// 3. questions qui construisent la liste des pièces, 4. ordre de la visite.
class PropertyWizardScreen extends StatefulWidget {
  const PropertyWizardScreen({super.key});

  @override
  State<PropertyWizardScreen> createState() => _PropertyWizardScreenState();
}

class _PropertyWizardScreenState extends State<PropertyWizardScreen> {
  final _infoForm = GlobalKey<FormState>();
  final _addressForm = GlobalKey<FormState>();
  final _c = {
    for (final k in ['title', 'description', 'address', 'neighborhood', 'city', 'rent',
      'charges', 'deposit', 'visit_fee'])
      k: TextEditingController(),
  };
  String _type = 'apartment';
  final _answers = RoomPlanAnswers();
  final _otherRoom = TextEditingController();

  int _step = 0;
  bool _busy = false;
  String? _error;
  OwnerProperty? _property;
  List<Room> _rooms = [];

  OwnerApi get _api => context.read<OwnerApi>();

  @override
  void initState() {
    super.initState();
    _c['city']!.text = 'Lomé';
  }

  @override
  void dispose() {
    for (final c in _c.values) {
      c.dispose();
    }
    _otherRoom.dispose();
    super.dispose();
  }

  int _int(String key) => int.tryParse(_c[key]!.text.replaceAll(RegExp(r'\s'), '')) ?? 0;

  Future<void> _run(Future<void> Function() task) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await task();
    } on ApiException catch (e) {
      setState(() => _error = e.fieldErrors.isEmpty
          ? e.message
          : e.fieldErrors.entries.map((f) => '${f.key} : ${f.value}').join('\n'));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _next() {
    switch (_step) {
      case 0:
        if (_infoForm.currentState!.validate()) setState(() => _step = 1);
      case 1:
        if (!_addressForm.currentState!.validate()) return;
        _run(() async {
          // Le brouillon n'est créé qu'une fois : un retour arrière ne crée pas de doublon.
          _property ??= await _api.create({
            'property_type': _type,
            'title': _c['title']!.text.trim(),
            'description': _c['description']!.text.trim(),
            'address': _c['address']!.text.trim(),
            'neighborhood': _c['neighborhood']!.text.trim(),
            'city': _c['city']!.text.trim(),
            'rent': _int('rent'),
            'charges': _int('charges'),
            'deposit': _int('deposit'),
            'visit_fee': _int('visit_fee'),
          });
          setState(() => _step = 2);
        });
      case 2:
        _run(() async {
          final p = await _api.applyRoomPlan(_property!.id, _answers);
          setState(() {
            _property = p;
            _rooms = [...p.rooms];
            _step = 3;
          });
        });
      case 3:
        _run(() async {
          await _api.reorderRooms(_property!.id, [for (final r in _rooms) r.id]);
          if (!mounted) return;
          Navigator.of(context).pushReplacement(MaterialPageRoute(
            builder: (_) => OwnerPropertyScreen(propertyId: _property!.id),
          ));
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nouveau bien')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: Stepper(
            currentStep: _step,
            onStepContinue: _busy ? null : _next,
            onStepCancel: _step == 0 || _busy ? null : () => setState(() => _step -= 1),
            controlsBuilder: (context, details) => Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Row(
                children: [
                  FilledButton(
                    onPressed: details.onStepContinue,
                    child: _busy
                        ? const SizedBox.square(
                            dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                        : Text(_step == 3 ? 'Passer aux photos' : 'Continuer'),
                  ),
                  if (_step > 0) ...[
                    const SizedBox(width: 8),
                    TextButton(onPressed: details.onStepCancel, child: const Text('Retour')),
                  ],
                ],
              ),
            ),
            steps: [
              Step(
                title: const Text('Le bien'),
                isActive: _step >= 0,
                content: _withError(_infoStep()),
              ),
              Step(
                title: const Text('Adresse et prix'),
                isActive: _step >= 1,
                content: _withError(_addressStep()),
              ),
              Step(
                title: const Text('Les pièces'),
                subtitle: const Text('Quelques questions pour préparer la visite'),
                isActive: _step >= 2,
                content: _withError(_questionsStep()),
              ),
              Step(
                title: const Text('Ordre de la visite'),
                isActive: _step >= 3,
                content: _withError(_orderStep()),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _withError(Widget child) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [if (_error != null) ErrorBanner(_error!), child],
      );

  InputDecoration _dec(String label, {String? helper, String? suffix}) => InputDecoration(
        labelText: label,
        helperText: helper,
        suffixText: suffix,
        border: const OutlineInputBorder(),
      );

  Widget _infoStep() => Form(
        key: _infoForm,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final e in propertyTypes.entries)
                  ChoiceChip(
                    label: Text(e.value),
                    selected: _type == e.key,
                    onSelected: (_) => setState(() => _type = e.key),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _c['title'],
              decoration: _dec('Titre de l\'annonce', helper: 'Ex. Appartement 2 chambres à Bè'),
              validator: requiredField,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _c['description'],
              decoration: _dec('Description courte'),
              maxLines: 3,
            ),
          ],
        ),
      );

  Widget _money(String key, String label, {bool required = false}) => TextFormField(
        controller: _c[key],
        keyboardType: TextInputType.number,
        decoration: _dec(label, suffix: 'FCFA'),
        validator: (v) {
          if (required && (v == null || v.trim().isEmpty)) return 'Champ obligatoire';
          if (v != null && v.trim().isNotEmpty && int.tryParse(v.replaceAll(' ', '')) == null) {
            return 'Nombre entier attendu';
          }
          return null;
        },
      );

  Widget _addressStep() => Form(
        key: _addressForm,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextFormField(
              controller: _c['address'],
              decoration: _dec('Adresse'),
              validator: requiredField,
            ),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(
                child: TextFormField(
                  controller: _c['neighborhood'],
                  decoration: _dec('Quartier'),
                  validator: requiredField,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextFormField(
                  controller: _c['city'],
                  decoration: _dec('Ville'),
                  validator: requiredField,
                ),
              ),
            ]),
            const SizedBox(height: 16),
            _money('rent', 'Loyer mensuel', required: true),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: _money('charges', 'Charges')),
              const SizedBox(width: 12),
              Expanded(child: _money('deposit', 'Caution')),
            ]),
            const SizedBox(height: 16),
            _money('visit_fee', 'Frais de réservation de visite'),
          ],
        ),
      );

  Widget _segmented(String label, String value, Map<String, String> options,
          ValueChanged<String> onChanged) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final o in options.entries)
                  ChoiceChip(
                    label: Text(o.value),
                    selected: value == o.key,
                    onSelected: (_) => setState(() => onChanged(o.key)),
                  ),
              ],
            ),
          ],
        ),
      );

  Widget _questionsStep() {
    final a = _answers;
    const place = {'interior': 'À l\'intérieur', 'exterior': 'À l\'extérieur', 'none': 'Aucune'};
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text('Combien de chambres ?', style: Theme.of(context).textTheme.titleSmall),
            ),
            IconButton.outlined(
              tooltip: 'Une chambre de moins',
              onPressed: a.bedrooms > 0 ? () => setState(() => a.bedrooms--) : null,
              icon: const Icon(Icons.remove),
            ),
            SizedBox(
              width: 40,
              child: Text('${a.bedrooms}',
                  textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleLarge),
            ),
            IconButton.outlined(
              tooltip: 'Une chambre de plus',
              onPressed: a.bedrooms < 10 ? () => setState(() => a.bedrooms++) : null,
              icon: const Icon(Icons.add),
            ),
          ],
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Il y a un salon'),
          value: a.livingRoom,
          onChanged: (v) => setState(() => a.livingRoom = v),
        ),
        const SizedBox(height: 8),
        _segmented('Cuisine', a.kitchen, place, (v) => a.kitchen = v),
        _segmented('Douche', a.bathroom, place, (v) => a.bathroom = v),
        _segmented('WC', a.toilet, {
          if (a.bathroom != 'none') 'with_bathroom': 'Dans la douche',
          ...place,
        }, (v) => a.toilet = v),
        Text('Espaces ouverts', style: Theme.of(context).textTheme.titleSmall),
        Wrap(
          spacing: 8,
          children: [
            FilterChip(
              label: const Text('Balcon'),
              selected: a.balcony,
              onSelected: (v) => setState(() => a.balcony = v),
            ),
            FilterChip(
              label: const Text('Terrasse'),
              selected: a.terrace,
              onSelected: (v) => setState(() => a.terrace = v),
            ),
            FilterChip(
              label: const Text('Cour'),
              selected: a.yard,
              onSelected: (v) => setState(() => a.yard = v),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text('Autres espaces', style: Theme.of(context).textTheme.titleSmall),
        Wrap(
          spacing: 8,
          children: [
            for (final o in a.others)
              InputChip(label: Text(o), onDeleted: () => setState(() => a.others.remove(o))),
          ],
        ),
        if (a.others.length < 5)
          TextField(
            controller: _otherRoom,
            decoration: const InputDecoration(
              hintText: 'Ex. Bureau, buanderie… puis Entrée',
              prefixIcon: Icon(Icons.add),
            ),
            onSubmitted: (v) {
              if (v.trim().isEmpty) return;
              setState(() => a.others.add(v.trim()));
              _otherRoom.clear();
            },
          ),
      ],
    );
  }

  Widget _orderStep() => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Le visiteur parcourra les pièces dans cet ordre. '
              'Faites glisser une pièce pour la déplacer.'),
          const SizedBox(height: 12),
          ReorderableListView(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            buildDefaultDragHandles: false,
            onReorderItem: (from, to) => setState(() => _rooms.insert(to, _rooms.removeAt(from))),
            children: [
              for (final (i, r) in _rooms.indexed)
                ListTile(
                  key: ValueKey(r.id),
                  leading: CircleAvatar(child: Text('${i + 1}')),
                  title: Text(r.name),
                  subtitle: r.isExterior ? const Text('Extérieur') : null,
                  trailing: ReorderableDragStartListener(
                    index: i,
                    child: const Icon(Icons.drag_handle),
                  ),
                ),
            ],
          ),
        ],
      );
}
