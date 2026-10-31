# BactoMate — résumé des modifications

Version BactoMate_custom préparée pour les essais de l’équipe, le 28 octobre 2026.

Base de comparaison : BactoMate 2.9.5, commit `2dfd181` du dépôt
`santinlab-code/BactoMate`. Les changements décrits ici sont regroupés dans la branche
`test/bactomate-optimisations` de GitHub, pour les essais.

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

L’image s’ouvre par défaut dans une fenêtre séparée, déplaçable sur un second
écran. **Attach image** la réintègre ; **Detach image** la détache à nouveau.
Fermer la fenêtre d’image la réintègre sans fermer les réglages.

Choisir **Cells** ou **Foci — current channel**, puis cliquer sur un objet dans
l’image sélectionne sa ligne de table. Un cadre jaune signale l’objet choisi,
y compris lors d’une sélection dans la table. Un clic sans objet désélectionne.
La touche **Supprimer** ou **Retour arrière** exclut la sélection active lorsque
l’image ou une table a le focus clavier. Cette exclusion est réversible.

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
leur aire en µm², leur longueur et leur largeur en µm, ainsi que leur position.
Les dimensions sont les grand et petit axes de l’ellipse équivalente au masque
(même méthode que les mesures morphologiques), pas une longueur de squelette.
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

La dernière exécution complète des tests automatisés donne **544 tests réussis,
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

## Ajouts BactoMate_custom — 28 octobre 2026

Le bouton Apply current filters conserve le canal choisi dans View. Le signal
Qt du bouton est traité comme un clic, pas comme un identifiant de canal.
La table des cellules ajoute Length (px) et Width (px) ; sa visibilité reste inchangée.

Les boutons Import/Save en double ont été retirés du panneau de gauche ; ceux
au-dessus de Cell filtering restent accessibles. Exclude cells at border est
coché pour les nouveaux réglages (les choix enregistrés restent respectés).
Les commandes manuelles Keep/Exclude/Use filters sont placées sous Cell filtering,
hors du panneau repliable Cell table / History.

L’aperçu des distances propose désormais un menu Images / channels à cocher
pour superposer phase et fluorescence, des LUT Min/Max/couleur/Auto par image,
un sélecteur de masque/position XY et des aides (?) sur les deux distances.
Les boutons ← Cell / Cell → et les touches fléchées naviguent entre cellules.
La molette zoome autour du pointeur dans les deux vues. Les LUT et la visibilité
des images ne changent pas les résultats de colocalisation.

## Ajustements après essais sur Mac — 28 octobre 2026

- Segmentation (Omnipose et U-Net) : Detach image ouvre le même canevas dans une
  fenêtre séparée. Attach image ou fermer cette fenêtre le réintègre. Les réglages
  et la LUT restent dans le panneau principal.
- Filtering : un clic gauche simple sélectionne l’objet et sa ligne de table,
  même après zoom ou déplacement. Glisser conserve le déplacement de l’image.
  Delete ou Backspace exclut la sélection ; Keep/Use filters permet de revenir
  sur ce choix. La sélection reste signalée par un cadre jaune.
- Cell table : aire en µm², longueur et largeur en µm, avec la calibration de
  Filtering. Changer la calibration actualise les valeurs. Sans calibration valide,
  les mesures physiques affichent un tiret. X/Y restent en pixels.
- Preview distances : l’histogramme interactif LUT de BactoMate remplace les
  champs numériques. LUT channel choisit le canal à ajuster ; chaque canal garde
  son intervalle. Les lignes Min/Max se déplacent à la souris. Auto LUT reste
  disponible. Le zoom à la molette est limité à environ 5 % par événement.

Validation de ces ajustements : 44 tests ciblés réussis, dont un vrai clic souris
sur une image zoomée/déplacée suivi de Delete, les dimensions calibrées et
les interactions des LUT. Chargement et affichage vérifiés sur les trois XY
réelles disponibles. Les essais natifs sur Mac restent à faire.

## Commandes dans l’image détachée et navigation directe — 28 octobre 2026

Les commandes Keep/Exclude/Use filters et le même histogramme LUT suivent
maintenant l’image Filtering détachée. Les LUT suivent aussi l’image en
Segmentation. Rattacher l’image restaure les widgets et leurs valeurs.
Un clic droit sur un objet détecté le garde, ou garde toute la sélection si
l’objet en fait déjà partie. Le fond n’ajoute aucun objet ; les foci restent
propres au canal actif.
Dans Preview distances, les icônes Maison et déplacement sont retirées :
maintenir le clic gauche et glisser déplace l’image dans chacune des deux vues,
sans changer la cellule. Un clic simple sélectionne toujours une cellule.
Les boutons de cellule précédente/suivante restent disponibles.

## Section Analysis — 31 octobre 2026

Ajoutée uniquement à BactoMate_Custom_Analyses ; V1 n’est pas modifiée.
Une section autonome permet de charger les tables CSV/TSV/Excel, choisir les
métriques et groupes, filtrer et produire 11 types de figures. Les profils réels
peuvent être extraits de masques et images de fluorescence par squelette médian
ou projection droite. Démographes, kymographes avec identités vérifiées et cartes
sur cellule normalisée sont disponibles. La normalisation des intensités est
explicite et les valeurs brutes restent présentes.
Chaque export contient PNG/PDF/SVG, un tableur XLSX, les CSV utilisés, les paramètres,
les empreintes des fichiers et des scripts de reproduction Python/R/MATLAB.
Les scripts redessinent les primitives calculées afin de garder les mêmes KDE,
quartiles et couleurs, avec des différences de rendu possibles entre logiciels.
Python est testé par exécution ; R et MATLAB restent à vérifier dans ces logiciels.
Le guide complet et la référence MicrobeJ sont dans docs/ANALYSIS_FR.md.

Validation du 31 octobre : 570 tests réussis, 5 ignorés. Les scripts Python
sont exécutés pour chacun des 11 types de figure. Un démographe GFP a été
extrait et exporté sur les 144 cellules réelles de XY001.

## LUT par canal et fenêtres détachées — 31 octobre 2026

La LUT partagée mémorise maintenant les contrastes par image/canal pendant la
navigation dans un aperçu. Conversion, Filtering, contours FI et U-Net utilisent
ce mécanisme ; Omnipose identifie aussi le fond/canal sélectionné. Les changements
de frame ou les remises à zéro historiques de navigation ne remplacent plus la
LUT d’un canal déjà réglé. Les montages et l’aperçu des distances avaient déjà
leurs valeurs séparées. Il ne s’agit pas d’une sauvegarde sur disque après fermeture.

Les fenêtres d’image détachées ne disparaissent plus sur Échap. La LUT est à
droite, dans un panneau adapté en largeur. Recenter / fit image restaure la vue
d’ensemble ; les glissières horizontale et verticale suivent le centre visible
et permettent de le déplacer. Rattacher l’image restitue la disposition initiale.
Dans Foci distances, les canaux à afficher sont des cases directement visibles.

Validation : 574 tests réussis, 5 ignorés ; six tests ciblés ont ensuite
revalidé la mémoire des LUT, Échap, le panneau latéral et les glissières après
l’ajustement de disposition. Le rendu de la fenêtre détachée a été relu.

## Filtering : panneau fixe et curation des foci — 31 octobre 2026

Les cartes Cell filtering et Foci filtering restent fixes et côte à côte. Les
tables et historiques disposent de deux onglets avec dix lignes de table visibles.
Le détachement de l’image ne laisse plus de grands espaces avant les réglages.
Les cellules sont dessinées en contours blancs fins sans remplissage.
Dans un canal de foci, cliquer choisit le focus du canal actif, avec sa ligne de
table. Delete l’exclut sans modifier sa cellule. Tous les marqueurs proviennent
des détections CSV : vert pour conservé, rouge pour rejeté/exclu. Les CSV originaux
sont prioritaires pour conserver les foci rejetés à l’écran et dans la table.

Validation : 577 tests réussis, 5 ignorés. Après les derniers ajustements du
clic droit et de l’historique partagé, 13 tests ciblés réussissent également.
Le parcours réel de l’interface vérifie les couleurs, le clic gauche, Delete,
le clic droit, la conservation de la cellule et la disposition détachée.

## Filtering : couleur et contours des cellules retenues — 31 octobre 2026

Le sélecteur de couleur est disponible près de Show cell contours et dans la
fenêtre détachée. Filtering mémorise sa couleur, avec du blanc par défaut.
Seules les cellules retenues après filtrage et curation ont un contour ; une
sélection vide ne dessine aucun contour. Les objets rejetés restent disponibles
dans la table pour être réintégrés. Le changement de couleur ne recalcule ni
segmentation ni filtres, et ne change pas les mesures ou les masques sources.

Validation : 579 tests réussis, 5 ignorés. Les tests couvrent la couleur
mémorisée, l’annulation du dialogue, l’absence de recalcul, les cellules
rejetées, la sélection vide et la réintégration manuelle.

## Nouvelle interface Analysis — branche New-Analyses

La branche BactoMate_Custom_New-Analyses est une copie de BactoMate_Custom_Analyses
au commit 53ec722. Les branches précédentes restent inchangées.
Les résultats du projet sont chargés automatiquement à l’entrée dans Analysis,
avec cache des fichiers inchangés et signalement des fichiers non lus. Les tables
cellulaires ne sont pas mélangées avec les résumés, les foci ou les trajectoires.
L’interface simple propose données, figure, mesure et attribution conditions/
réplicats. Les attributions, modifiables par lot, sont conservées dans
analysis_groups.json. Les XY d’un même réplicat peuvent partager le même nom.
Un violon représente les observations cellulaires ; les points colorés montrent
les moyennes des réplicats par condition. L’export contient leur table dédiée.
Un choix de frame évite de regrouper implicitement les observations d’un film.
Les onze figures et les autres réglages restent disponibles en mode avancé.
Le parcours complet est décrit dans docs/NEW_ANALYSIS_FR.md.

Validation : 585 tests réussis, 5 ignorés. Les retouches des libellés et du
mode avancé ont ensuite été vérifiées par 24 tests ciblés, puis les six tests
du parcours guidé ont été rejoués avec succès après le contrôle du bouton
d’export avancé. Le parcours automatique X/Y et R1/R2 a été relu dans la fenêtre
principale. Le script Python exporté avec les réplicats est exécuté dans les tests.

## Session, LUT et sélection XY — 31 octobre 2026

L’accueil propose Clear current session. Ce bouton ferme les prévisualisations,
vide les chemins et les données Analysis (figures, cache et attributions en
mémoire), puis revient à l’accueil. Les fichiers et les attributions enregistrées
sur disque restent présents. Une tâche doit être terminée ou annulée avant la
remise à zéro.

Dans les images détachées, les LUT sont ouvertes directement dans le panneau
latéral, sans en-tête repliable. Le rattachement retrouve l’état du panneau intégré.
La prévisualisation Foci distances affiche aussi ses LUT sans repli.

Filtering propose Mask / XY position au-dessus des réglages et tables. Le choix
recharge le masque, les foci, les tables et la curation de ce XY ; il met aussi
à jour le chemin cible de Filter File/Folder. Les paramètres de filtrage sont
conservés. Le changement est bloqué pendant un calcul de filtrage.

À la fin d’Analyze, les résultats finaux sont chargés automatiquement, après les
mesures complémentaires et la fusion des canaux. Une fois les données chargées,
BactoMate ouvre Analysis. Cela fonctionne pour un fichier ou un lot de fichiers,
y compris avec des sorties dans plusieurs sous-dossiers. La recherche à partir
d’un masque remonte au dossier de l’échantillon pour trouver le dossier voisin
_analysis, même depuis _segmentation*/filtered_masks.

Validation : suite complète de 588 tests réussis, 5 ignorés ; puis six tests
ciblés réussis, incluant le lot de classeurs fusionnés et le refus de remise à
zéro pendant un calcul de prévisualisation. L’accueil, les tables Filtering avec
le sélecteur XY et le panneau LUT détaché ont été contrôlés visuellement.

## Analysis : guide de figures et rendu publication — 31 octobre 2026

La section Analysis est en anglais. Conditions & replicates reste tout en haut,
en mode simple comme avancé. Les attributions déjà enregistrées restent valides.
Le bouton Figure guide propose quatre étapes : question, population, apparence,
puis récapitulatif et tracé. Il couvre distributions, relations entre mesures,
démographes, cartes des maxima et pourcentages de cellules par nombre de foci.
Le mode Advanced / MicrobeJ-style controls conserve les réglages libres et les
imports manuels ; ce nom ne désigne pas une intégration du plugin Fiji lui-même.

Les vues spatiales retrouvent les masques et canaux du projet sans sélection
manuelle de fichiers. Les masques filtrés sont prioritaires, et les masques non
filtrés sont signalés au récapitulatif. Le calcul utilise les pixels réels et
reste en tâche de fond. Une sélection de condition et de frame limite la population.
Les démographes ont une ligne par cellule, un axe longitudinal 0–1 et un tri par
longueur. La carte des maxima distingue explicitement le pixel le plus brillant
par cellule des foci conservés dans les CSV de Filtering. Elle montre les points,
une densité relative et un contour schématique. Les coordonnées sources restent
exportées. L’alignement explicite du pôle le plus brillant place ce pôle à gauche/
en haut ; il ne déduit pas l’âge des pôles.

Les figures et exports sont carrés : 6 × 6 pouces, PNG 1800 × 1800 à 300 dpi,
PDF et SVG. Les scripts exportés conservent aussi un canevas carré. Le guide
anglais est décrit dans docs/FIGURE_GUIDE.md.

Validation : 598 tests réussis, 5 ignorés dans la suite complète. Les retouches
d’affichage et de reprise des choix ont ensuite été vérifiées par 33 tests
ciblés, puis les sept tests du guide ont été rejoués avec succès. Le parcours
utilise de vrais artefacts de test, sans dialogue d’import, et vérifie l’exclusion
des cellules rejetées, le changement de projet pendant un calcul, les zéros des
comptages et l’exécution du script Python exporté. Deux contrôles finaux valident
la carte des maxima et la reprise des choix avec remise à zéro des anciens filtres.
Des aperçus issus de données simulées figurent dans docs/FIGURE_GUIDE.md.
