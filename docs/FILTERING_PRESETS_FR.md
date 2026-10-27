# Réutiliser les réglages de Filtering

Dans Filtering, ou dans son aperçu, **Save filter settings…** enregistre un fichier
JSON par type : `.cells.json` pour les cellules, `.foci_01_GFP.json` pour GFP,
`.foci_02_mCh.json` pour mCh (les noms et l’ordre dépendent des canaux présents).
**Import filter settings…** charge un fichier à la fois et actualise l’aperçu ouvert.
Un fichier de cellules ne change que les filtres des cellules ; un fichier de foci
ne change que le canal nommé dans le fichier. Les autres réglages sont conservés.
Les anciens fichiers regroupant tous les réglages restent importables.
Attendre la fin d’un filtrage avant de charger d’autres réglages.

Les fichiers contiennent tous les filtres des cellules et les filtres des foci par canal,
y compris les cases activées/désactivées, les seuils et la taille de pixel.
Les canaux sont reconnus par leur nom : conserver les mêmes noms (par exemple GFP
et mCh) lors des analyses suivantes. Un nouveau canal utilise les réglages par
défaut du fichier. Vérifier la calibration des nouvelles images : les métadonnées
de taille de pixel peuvent être prioritaires dans l’aperçu.

À chaque export **Filter File/Folder**, un fichier
`<nom_du_masque_filtré>.filter_settings.cells.json` et un fichier
`<nom_du_masque_filtré>.filter_settings.foci_<numéro>_<canal>.json` par canal
accompagnent chaque masque TIFF exporté.
Il peut être chargé pour une analyse future, sans avoir besoin des images d’origine.

Les choix manuels sur des cellules ou des foci précis restent dans leurs fichiers
de curation associés aux masques. Ils ne sont pas transférés vers d’autres images
par le fichier de réglages. L’historique reste également propre à chaque masque.

Le format porte l’identifiant `bactomate-filter-settings` et le numéro de version 1.
Un fichier incompatible ou invalide est refusé sans remplacer les réglages courants.
