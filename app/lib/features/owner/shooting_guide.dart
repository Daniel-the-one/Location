import 'package:material_ui/material_ui.dart';

/// Guide de prise de vue affiché avant les photos d'une pièce (section 5 du cahier).
class ShootingGuide extends StatelessWidget {
  const ShootingGuide({super.key, this.dense = false});

  final bool dense;

  static const tips = [
    (Icons.my_location, 'Placez-vous au centre de la pièce, téléphone en portrait, '
        'à hauteur de poitrine (environ 1,4 m).'),
    (Icons.threesixty, 'Restez au même point et tournez sur vous-même, sans avancer.'),
    (Icons.photo_library_outlined, 'Prenez 12 photos, une tous les 30° (8 au minimum). '
        'Chaque photo doit reprendre un tiers de la précédente.'),
    (Icons.zoom_out_map, 'Ne zoomez pas et gardez la même luminosité.'),
    (Icons.light_mode_outlined, 'Allumez les lumières et ouvrez les volets.'),
    (Icons.do_not_step, 'Évitez les personnes et objets en mouvement.'),
  ];

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Comment prendre les photos', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            for (final (icon, text) in tips)
              Padding(
                padding: EdgeInsets.symmetric(vertical: dense ? 2 : 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
                    const SizedBox(width: 12),
                    Expanded(child: Text(text)),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
