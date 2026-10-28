# Sélection manuelle et suivi du filtrage

L’image de Filtering est détachée par défaut pour être déplacée sur un autre écran.
**Attach image** (ou fermer la fenêtre d’image) la réintègre ; **Detach image**
la détache à nouveau. Les réglages restent dans l’interface principale.
Choisir **Cells** ou **Foci — current channel** dans la fenêtre d’image, puis
cliquer sur un objet sélectionne sa ligne de table. Un cadre jaune marque la
sélection, également lorsqu’elle vient de la table. Cliquer sans objet désélectionne.
Avec le focus clavier dans l’image ou une table, **Supprimer** ou **Retour arrière**
exclut les objets sélectionnés. Ce choix reste réversible avec **Keep selected objects**
ou **Use filters for selected objects**. Le clavier n’exclut rien pendant un calcul.

Dans l’aperçu de **Filtering**, ouvrir **Cell table / Manual selection / History**.
La sélection manuelle porte sur des objets déjà détectés : elle ne dessine pas
de nouvelles cellules ou de nouveaux foci et ne modifie pas les masques sources.

## Cellules

La table indique l’identifiant de chaque cellule, si elle est retenue, sa surface
en pixels carrés et son centre. Choisir une ou plusieurs lignes (Ctrl/Cmd pour une
sélection multiple). Un double-clic centre l’image sur la cellule. Un clic sur
une cellule dans l’image sélectionne sa ligne.

- **Keep selected objects** : retenir les objets même si les filtres les rejettent.
- **Exclude selected objects** : exclure les objets même si les filtres les acceptent.
- **Use filters for selected objects** : retirer le choix manuel pour ces objets.

Les règles sont recalculées après chaque action, avec les choix manuels appliqués
en dernier. Les boutons sont désactivés pendant le calcul.

## Foci

Afficher la **Foci table** existante, puis choisir **Foci — nom du canal** dans
le nouveau panneau. Sélectionner les lignes et utiliser les mêmes boutons.
Un clic près d’un focus dans l’image sélectionne le focus le plus proche dans
ce canal (distance maximale de dix pixels natifs). Les choix GFP et mCherry
sont indépendants. La table et l’export CSV prennent en compte la sélection manuelle.

## Historique

Le menu présente les effectifs avant et après chaque application et chaque
action manuelle, avec le total segmenté et la variation. Les valeurs des filtres
de l’étape choisie sont affichées sous le menu. Les effectifs de foci sont
séparés par canal. Les chiffres concernent **l’instant affiché**, pas la somme du
film entier. L’historique ne sert pas à restaurer un ancien état.

Les filtres sont réappliqués aux objets sources ; une réintégration reste donc
possible. Les choix sont propres à chaque fichier, instant et canal. Ils sont
enregistrés dans un fichier `.curation.json` à côté du masque source et repris
lors de l’export des masques et des CSV filtrés. Conserver ce fichier avec les
masques pour retrouver la curation et l’historique après fermeture.

Une empreinte du masque protège contre la réutilisation des choix sur une nouvelle
segmentation. Si les masques sont remplacés, l’ancien fichier de curation doit
être archivé avant de recommencer.

## Validation

Les tests couvrent garder/exclure/retour aux filtres, plusieurs instants et
canaux, sauvegarde et réouverture, historique, sélection multiple et exports
TIFF et CSV. L’essai sur le ND2 fourni utilise les 144 cellules segmentées de
XY001, avec un filtre de surface et des corrections manuelles, vérifiées dans
le TIFF exporté. Les tests de foci utilisent des données contrôlées ; la
détection réelle GFP/mCherry sera évaluée à l’étape dédiée.

La table affiche Area (µm²), Length (µm) et Width (µm), calculés avec la
calibration Pixel size de Filtering. Les axes de l’ellipse équivalente donnent
longueur et largeur. X/Y sont les coordonnées du centre en pixels.
Un clic gauche simple sélectionne la cellule sous le pointeur ; un glisser
sert à déplacer l’image. Le clic tient compte du zoom et du déplacement.

Dans la fenêtre détachée, les commandes Keep selected objects / Exclude selected
objects / Use filters for selected objects et la LUT sont accessibles avec l’image.
Rattacher l’image remet ces contrôles dans le panneau d’origine, avec leurs valeurs.
Le clic droit sur un objet détecté le garde dans la sélection, même s’il avait été
exclu. Si l’objet appartient déjà à une sélection multiple, le clic droit garde
cette sélection entière. Cliquer droit dans le fond n’ajoute rien. Cette commande
ne dessine pas de nouveaux objets. Pour les foci, elle concerne le canal actif.
