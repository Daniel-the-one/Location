# Commit-sheet — Essivivi, site vitrine public

Surface : site vitrine statique, une seule page longue, complémentaire de l’application
Flutter déjà livrée dans `app/`. Public : locataires et propriétaires au Togo, avant le
rendu du 30 novembre 2026. Stack : HTML/CSS/JS natif, sans build, déployable en Static Site.

## 1. Peak — la signature

**Une fenêtre de visite 360° manipulable dans le hero** : le visiteur fait glisser le
panorama d’un salon pour regarder autour de lui. Ce n’est pas une décoration, c’est une
démonstration littérale du produit (« on visite avant de visiter »). Un curseur discret
« glissez pour regarder » rend l’affordance explicite au premier regard.

## 2. Color

- Ancre de marque relevée dans `app/lib/main.dart` : `#1F6F5C` → `oklch(0.47 0.085 166)`.
- Surface de page : `oklch(0.97 0.006 166)` — un blanc à peine teinté vers le vert de
  marque. **Pas de crème** : la chroma reste à 0.006, largement sous le seuil de la bande
  `L 0.84–0.97 / C < 0.06 / hue 40–100` bannie par le skill.
- Niveau d’engagement : **committed** — le vert porte la bande d’ouverture, les bandeaux
  de rupture, les boutons primaires et les accents, soit environ 35–45 % des surfaces vues.
- Mean lightness visée de la page : **L ≈ 0.90**. Scène physique : quelqu’un cherche un
  logement en plein jour, sur un écran, dans une pièce lumineuse — rien ne justifie un
  « premium = dark ». Le drame vient de l’ombre portée sur les photographies, pas du fond.
- Texte : `oklch(0.25 0.035 166)` (vert d’encre, jamais du gris neutre sur fond teinté).
- Accent chaud unique : `oklch(0.72 0.12 62)` (terre cuite), utilisé **uniquement** pour
  le badge « nouveau » et le trait de survol — pas d’ambre, pas de néon.

Ce n’est pas du lavender (hue 250–290), pas du beige (chroma 0.006 vers 166, pas vers 60),
pas le réflexe « vert immo + badges de confiance » : le vert est ici la couleur du code
Flutter de production, pas une association de catégorie.

## 3. Type

- Display : **Newsreader** (serif éditorial, oeil humain, voix « habité, direct »).
- Texte : **DM Sans** (humaniste, x-height ouverte, vrai italique, chiffres tabulaires).
- Axe de contraste : serif éditorial + sans humaniste.
- Pourquoi pas Inter : c’est le défaut statistique 2024–2026, et il est déjà la base
  implicite de l’écosystème Material/Flutter；le site vitrine doit avoir sa propre voix
  sans renier l’application.
- Échelle fluide `clamp()`, plafond display 5.5rem (le titre est dans le flux, pas un
  wordmark), `letter-spacing: -0.035em`, `text-wrap: balance`, corps 1.5, mesure 68ch.

## 4. Grid break

Le hero est un **split 7/5 asymétrique** (texte 7, fenêtre 5) et la fenêtre panoramique
**déborde de sa colonne** de 8 % vers la droite, chevauchant la bande vert foncé qui ferme
le hero. À l’inverse, la section « Visite virtuelle » inverse le rapport en 4/8 avec une
image pleine hauteur qui mord sur la bande suivante. Aucune grille de cartes symétrique
dans la page : les logements sont une liste éditoriale (1 grand + 2 petits), pas un `3×N`.

## 5. Budget motion

Deux familles seulement :
1. **Reveal au scroll** — opacité + translation 12 px vers le haut, `ease-out-quart`
   620 ms, stagger 60 ms. Une seule famille, exprimée différemment selon le contenu
   (les images montent de 16 px et passent de `scale(0.97)` à 1, le texte de 12 px).
2. **Panorama piloté** — `transform: translate3d()` direct sur le calque, sans état React,
   avec inertie courte à la fin du glisser.

Le hero a une entrée unique (opacité + `scale(0.97)`), qui n’est pas une troisième famille
de scroll. Aucun marquee. Aucun scroll-jacking. `prefers-reduced-motion` = alternatives
opacité seule, sans translation ni glisser automatique.

## 6. Reflex check

- **1er ordre** (site immobilier généré) : fond blanc, grille 3 colonnes de cartes
  identiques avec prix gras, badges « vérifié », illustration 3D de clé, compteurs
  « 500+ biens ». → écarté : pas de grille de cartes, pas de compteurs décoratifs.
- **2e ordre** (le « anti-immobilier » que produit un modèle qui évite le 1er) : fond
  noir, serif géant, photos désaturées déstructurées. → écarté : page claire à L≈0.90,
  photographies en couleur, hiérarchie lisible.
- **Déviation choisie** : le produit lui-même est la visite. La page est organisée autour
  d’une fenêtre qu’on manipule ; les annonces ne sont qu’une preuve, jamais le héros.
  Les chiffres affichés (loyers en FCFA, nombre de pièces) viennent du backend Django,
  pas d’un inventaire marketing inventé.

## 7. House tells cassés

1. **Near-black par défaut** → cassé : surface à L 0.97, bande d’accent à L 0.47, pas de
   `L < 0.25`. Remplacé par le contraste entre le vert de marque et le papier clair.
2. **Wordmark-as-hero** → cassé : le hero porte une photographie manipulable et une
   phrase (« Visitez la pièce avant de passer la porte. ») ; le nom « Essivivi » reste à
   l’échelle d’un logo dans l’en-tête.
3. **Status bar** (logo à gauche · statut au centre · action à droite) → cassé : la nav
   est à droite du logo, sans indicateur d’état ni pastille live ; l’action principale est
   dans le hero et dans la bande finale, pas dans le coin supérieur droit.

---

Décisions prises sans l’utilisateur (il dormait) : site vitrine statique plutôt qu’une
seconde application web, `web/` isolé de `app/` et `backend/`, images Pexels téléchargées
localement avec manifeste d’attribution.
