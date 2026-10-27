# BactoMate — résumé des modifications

Version de travail préparée pour les essais de l’équipe, le 27 octobre 2026.

Base de comparaison : BactoMate 2.9.5, commit `2dfd181` du dépôt
`santinlab-code/BactoMate`. Les changements décrits ici sont présents dans le
code de l’archive de test ; ils n’ont pas encore été envoyés sur GitHub.

## 1. File Conversion : fichiers ND2 avec plusieurs positions XY

**Avant :** la conversion ne permettait pas de récupérer correctement toutes
les positions d’un même fichier ND2.

**Maintenant :** chaque position XY est exportée séparément, avec ses canaux.
Les noms comportent `XY001`, `XY002`, etc. Les réglages de conversion existants
(temps, Z, sélection des canaux, recadrage et corrections) sont conservés.
La calibration est conservée. La reconnaissance des canaux phase Nikon PH3
a également été corrigée.

Sur le fichier de référence : **3 positions × 3 canaux = 9 TIFF**.
Les canaux sont GFP, mCherry et phase. La comparaison des pixels exportés
avec le ND2 a confirmé leur correspondance.

Le temps est conservé dans la pile TIFF de chaque position et canal pour les
films. Ce comportement a été vérifié sur des données synthétiques ; le fichier
de référence est une acquisition à un seul temps, donc il ne valide pas à lui
seul les films ND2 réels.

## 2. Segmentation : contours des cellules

**Avant :** un remplissage multicolore pouvait masquer les détails des cellules.

**Maintenant :** l’aperçu affiche des contours, avec une couleur au choix.
La couleur est mémorisée et les nouvelles images de contours exportées
utilisent ce réglage. Changer la couleur ne relance pas la segmentation et
ne modifie ni les masques ni les mesures.

L’affichage a été vérifié sur les trois positions du fichier de référence.
Cela valide le fonctionnement de l’affichage, pas la justesse biologique de
toutes les cellules segmentées.

## 3. Filtering : curation manuelle

Il est possible de sélectionner des cellules ou des foci déjà détectés pour :

- les garder dans la sélection, même si les filtres automatiques les rejettent ;
- les exclure de la sélection ;
- annuler le choix manuel et revenir à la décision des filtres.

Ces choix sont pris en compte dans l’aperçu et dans les résultats filtrés exportés.
Ils ne dessinent pas de nouveaux objets et ne suppriment pas les masques d’origine.
Les choix portent sur la frame courante ; pour les foci, ils sont également
propres au canal concerné.

Les décisions sont conservées dans un fichier `.curation.json` à côté du masque.
Garder ce fichier avec le masque permet de retrouver les choix plus tard.
Si une nouvelle segmentation change le masque, les anciens choix ne sont pas
réappliqués automatiquement à de nouveaux identifiants de cellules.

## 4. Filtering : table des cellules

Une table présente les identifiants des cellules, leur statut de sélection,
leur aire en pixels carrés et leur position.
On peut sélectionner plusieurs lignes ou cliquer sur une cellule dans l’image.
Un double-clic dans la table centre l’image sur la cellule.
La table des foci existante sert à sélectionner les foci du canal actif.

## 5. Filtering : effectifs et historique

Le panneau **Cell table / Manual selection / History** montre le nombre de
cellules sélectionnées par rapport au total.
L’historique garde les étapes de filtrage, les effectifs avant/après, leur
variation, les paramètres et les choix manuels associés. Les effectifs des
foci par canal sont renseignés lorsque les données sont disponibles.

Les effectifs affichés concernent la frame courante, pas la somme de tout le film.
L’historique documente les étapes ; il ne constitue pas un bouton de restauration
d’un ancien état.

## 6. Filtering : réglages indépendants par canal

**Correction :** changer de canal pouvait laisser les mêmes valeurs dans les
champs de réglage et les enregistrer pour le mauvais canal.

**Maintenant :** GFP et mCherry gardent chacun leurs seuils et leurs cases cochées.
Changer de canal dans **View** enregistre les valeurs du canal quitté et affiche
celles du canal choisi, même avant de cliquer sur Apply.
L’analyse utilise les réglages propres à chaque canal.

## 7. Filtering : fichiers de paramètres réutilisables

**Save filter settings…** enregistre des fichiers JSON séparés.
**Import filter settings…** permet de les charger un par un pour une future analyse.
L’export **Filter File/Folder** les produit aussi automatiquement à côté des
masques filtrés.

Exemples de suffixes sur le fichier de référence :

| Fichier | Contenu |
| --- | --- |
| `.filter_settings.cells.json` | Filtres des cellules sur la phase, dont la calibration |
| `.filter_settings.foci_01_CT_16bits_GFP.json` | Filtres des foci GFP |
| `.filter_settings.foci_02_CT_16bits_mcherry.json` | Filtres des foci mCherry |

Le préfixe dépend du nom du masque exporté et les numéros dépendent de l’ordre
des canaux. Le nom du canal est aussi inscrit à l’intérieur du fichier.

Importer un fichier GFP ne change pas les paramètres mCherry ni ceux des cellules.
Conserver les mêmes noms de canaux lors des analyses futures. Les anciens JSON
regroupant tous les réglages restent importables.
Les fichiers incompatibles sont refusés sans remplacer les réglages courants.

Les paramètres comprennent les seuils et l’activation des filtres, pas les
décisions manuelles sur des objets précis. Ces dernières restent dans les fichiers
de curation associés aux images d’origine.

## 8. Foci analysis : valeurs initiales de colocalisation

Les nouvelles valeurs par défaut sont :

| Paramètre | Avant | Maintenant |
| --- | --- | --- |
| Max distance | 8 px | **3 px** |
| Threshold | 4 px | **2 px** |

Max distance est le rayon dans lequel chercher un partenaire dans l’autre canal.
L’appariement est un-à-un. Threshold décide ensuite si une paire appariée est
comptée comme colocalisée, selon la distance entre les centres des foci.
Une session déjà enregistrée peut conserver ses propres valeurs.

## 9. Foci analysis : aperçu des distances

Le bouton **Preview distances…** ouvre une vue d’ensemble et un zoom sur une cellule.
On peut choisir la cellule, la frame, les deux canaux et le fond d’image disponible
(phase ou fluorescence).

- Centres des foci : cyan pour A, magenta pour B.
- Cercle jaune pointillé : rayon Max distance ; cercle vert : Threshold.
- Ligne verte : paire colocalisée ; ligne orange : paire appariée au-dessus du seuil.

Dans le zoom, la grille correspond à un pixel de l’image et un carré blanc
représente 1 px. La calibration en µm est indiquée lorsqu’elle est disponible.
Les cercles représentent des distances, pas le diamètre des foci.

Les paramètres changés dans cet aperçu mettent à jour Foci analysis.
L’aperçu utilise le même calcul d’appariement et l’option Same cell only que
l’analyse, sans réexécuter la détection ni écrire de résultats d’analyse.

Sans CSV de détection, les images et les cellules restent visibles avec un
message d’information. Aucun focus artificiel n’est ajouté.

## Vérifications et limites des essais

La dernière exécution complète des tests automatisés donne **542 tests réussis,
5 ignorés**. Une vérification ciblée de l’aperçu a également réussi après les
derniers ajustements.

Le fichier de référence est `2025-10-02-Snaps-AP-GL2430-GA178-Cd16.nd2`.
Les essais réels ont porté sur l’export des neuf TIFF, les contours des trois
positions, la curation et les exports sur la première position, ainsi que
l’affichage de l’aperçu des distances et de la calibration.

Les comportements des filtres des foci, des paramètres indépendants et des
paires de colocalisation ont été testés avec des données contrôlées. La détection
des foci, la colocalisation biologique et les mesures de fluorescence sur le
fichier réel restent à évaluer avec l’équipe. Le présent document ne certifie
pas leur qualité scientifique.

## Documentation complémentaire

- `GUIDE_TEST_BACTOMATE_FR.md` : installation et parcours d’essai.
- `docs/ND2_MULTIPOINTS_FR.md`
- `docs/SEGMENTATION_CONTOURS_FR.md`
- `docs/FILTERING_CURATION_FR.md`
- `docs/FILTERING_PRESETS_FR.md`
- `docs/FOCI_DISTANCE_PREVIEW_FR.md`
