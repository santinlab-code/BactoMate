# BactoMate Custom — installation et parcours de test

Mise à jour : **6 novembre 2026**, branche
**BactoMate_Custom_New-Analyses**.
[Version anglaise](GUIDE_TEST_BACTOMATE_EN.md) · [Bilan des changements](MODIFICATIONS_BACTOMATE_FR.md)

Utiliser une copie d’un petit jeu de données dans un dossier d’essai. Prévoir
plusieurs XY, phase, GFP/mCherry et un film suivi pour le kymographe. Noter commit,
OS, calibration et canaux. Ces contrôles ne valident pas la justesse biologique.
Les guides thématiques complémentaires sont en anglais.

## 1. Installation

Cloner/télécharger [la branche active](README.md#install-this-custom-version).
Les apps upstream ne garantissent pas la présence des ajouts custom. V1 et Analyses
ont été supprimées de GitHub. Utiliser Python 3.11 et créer le venv dans le dossier
final ; ne pas déplacer celui de l’ancienne installation.

Sur Mac, Terminal dans le dossier contenant `main.py` :

```bash
chmod +x setup/macos/*.sh launch_gui.sh
./setup/macos/install.sh
source venv/bin/activate
python main.py --version
python main.py --smoke-test
./launch_gui.sh
```

Sur Windows, invite de commandes dans le dossier du projet :

```bat
setup\windows\install.bat
venv\Scripts\python.exe main.py --version
venv\Scripts\python.exe main.py --smoke-test
launch_windows.bat
```

Le numéro peut rester 2.9.5 : `git rev-parse HEAD` identifie la révision custom.
Voir [setup](setup/README.md) pour mise à jour/réparations. Si installé directement
dans le dossier personnel, les futurs lancements Mac sont :

```bash
cd ~/BactoMate_custom
./launch_gui.sh
```

## 2. Accueil et session

Ouvrir un projet. Vérifier la section Analysis indépendante. Choisir des chemins,
puis Clear current session : retour accueil, chemins/caches vides, fenêtres
fermées. Les résultats et `analysis_groups.json` enregistrés restent sur disque.
Le reset ne doit pas interrompre silencieusement un calcul actif : le terminer
ou l’annuler d’abord.

## 3. Conversion ND2

Vérifier positions/canaux/rôles. Désactiver d’abord corrections/recadrage, séparer
les canaux et convertir. Trois XY × trois canaux doivent donner neuf TIFF dans
Tif_files. Comparer identité, nombre de frames, profondeur et calibration avec le
ND2 dans BactoMate/Fiji. L’aperçu montre le premier XY. Un fichier à un seul temps
ne valide pas la conversion d’un film.

## 4. Segmentation et détachement

Segmenter la phase avec le bon modèle. Vérifier contours, visibilité et couleur,
sans changement des labels lors d’un réglage d’affichage. Tester un petit fichier
avant un lot. Détacher : contrôles compacts en haut, LUTs ouvertes à droite,
molette douce, déplacement au clic maintenu, recentrage et glissières. Régler les
contrastes par canal, changer/revenir : chaque canal doit retrouver sa plage.
Échap garde l’image ouverte. Attach restaure la disposition et les valeurs.

Tester la croix : Cancel garde ouvert ; Save propose TIFF/JPEG ; annuler le chemin
garde ouvert ; Save réussi/Discard réintègre l’image. La vue sauvegardée est en RGB,
pas un masque scientifique.

## 5. Filtering : objets et tableaux

Choisir Mask / XY position. Tester les pages Cell table, Foci table, Cell filters
et Foci filters : dix lignes dans les tables, historiques sous les réglages des
pages de filtres respectives, champs intacts. Import/Save
apparaissent sur les pages de filtres. Tester des polices plus grandes, redimensionner,
attacher/détacher deux fois et déplacer le séparateur image/pages. Aucun chevauchement ;
le contenu doit rester accessible si la zone est trop petite, sans grand vide après détachement. Nouvelles recettes :
exclusion des cellules au bord et Exclude fully outside cochées ; les choix déjà
enregistrés peuvent remplacer ces défauts.

Vérifier aire en µm², longueur/largeur en µm, X/Y en pixels. Modifier la calibration
sur un XY d’essai : dimensions physiques actualisées, source inchangée. Longueur/
largeur correspondent à l’ellipse équivalente. Apply sur GFP doit garder View sur
GFP. Modifier LUT GFP/mCherry et naviguer rapidement : pas de réinitialisation.

| Action | Résultat attendu |
| --- | --- |
| Clic cellule en mode Cells | Ligne cellulaire correspondante |
| Clic focus dans son canal | Ligne du focus, pas de sa cellule |
| Maj-clic sur objets éloignés | Seulement les objets cliqués |
| Double-clic ligne cellule | Recentrage sur la cellule |
| Delete/Retour arrière | Exclusion réversible |
| Keep | Conservation manuelle prioritaire |
| Use filters | Suppression du choix manuel |
| Clic droit | Menu, sans ajout immédiat |

Contours uniquement sur cellules retenues, fins et couleur au choix ; foci verts
si retenus, rouges si rejetés/exclus. Exclure un focus doit garder sa cellule.
Tout rejeter doit enlever tous les contours cellulaires.

Créer un focus à un emplacement vide dans son canal, puis un polygone cellulaire.
Entrée/double-clic termine ; Échap annule un second tracé. Vérifier tables/exports,
marqueur manual pour les foci et absence de modification des sources.

## 6. Réglages indépendants et lot

XY1 : fixer filtres cellules/GFP/mCherry et calibration. Nouveau XY2 : il hérite
des valeurs ; les modifier. Retour XY1 : ses valeurs initiales doivent revenir.
Rouvrir l’aperçu et vérifier curation/recettes sauvegardées. Changer de canal sans
Apply préalable doit quand même conserver les valeurs.

Exporter les presets puis importer seulement GFP : mCherry/cellules inchangés.
Les décisions sur objets restent dans `.curation.json`. Après visite de plusieurs
XY, Filter File/Folder doit montrer le lot complet et l’état des résultats.
Exporter plusieurs XY et vérifier leurs recettes distinctes, masques/foci/presets.
Les variantes brute/filtrée sont regroupées lorsqu’elles correspondent. Les comptes
d’historique concernent la frame courante ; ce n’est pas une fonction Annuler.

## 7. Foci Distance Preview

Avec deux canaux détectés, ouvrir Preview distances. Session neuve : 3 px / 2 px.
Lire les (?), choisir XY/frame/cellule et tester boutons/flèches précédent/suivant.
Cocher plusieurs fonds, régler chaque LUT, vérifier leur conservation. Tester
molette douce et déplacement dans les deux vues.

Contrôler centres cyan/magenta, rayons de recherche/seuil, liens verts/orange et
titre Colocalized / Not Colocalized après changement de seuil. Sans CSV, message
informatif, pas de faux foci. L’aperçu ne doit pas écrire de tables d’analyse.

## 8. Analyze et chargement automatique

Terminer Analyze avec les options FI/foci/colocalisation voulues. Après les mesures
finales et fusions, Analysis doit s’ouvrir avec les données déjà chargées, y compris
sur plusieurs sous-dossiers. Cellules/foci/tracking/profils/résumés restent distincts.
Refresh results doit trouver les changements et signaler les illisibles. Les copies
connues CSV/XLSX/agrégats ne doivent pas doubler les observations.

## 9. Conditions, réplicats et violon

Attribuer X/Y et R1/R2/R3 par fichier dans Conditions & replicates. Donner le même
nom aux XY d’un même réplicat biologique. Sauvegarder/rouvrir et vérifier le JSON.
Cells → Violin plot → Cell area, Compare conditions, Show replicate means et choix
de frame : distribution des cellules et une moyenne colorée par réplicat/condition.
Vérifier la feuille/CSV Replicates exportée. Un XY ne devient pas automatiquement
un réplicat.

## 10. Guide, démographe, maxima et film

Suivre Question → Population → Appearance → Review/draw. Démographe : bon canal/
condition/frame, cellules retenues, enveloppe en colonnes triées par longueur et
alternative en lignes normalisées 0–1, avec 24 segments par défaut. Comparer les
trois intensités ; les cases manquantes ne doivent pas être
interprétées comme une fluorescence nulle. Le choix natif ajoute native_profiles.csv.

Maxima map : comparer brightest pixel et kept detected foci, contrôler axes
normalisés et densité relative de points. Foci count doit prendre un compte par
cellule, y compris les cellules à zéro focus.

Film : un XY/canal, masque Tracking et un ID vérifié. Confirmer la continuité,
indiquer l’intervalle si connu et tracer : au moins deux temps, position 0–1 et
temps en minutes ou frames. Des labels non liés ne doivent pas être suivis implicitement.

## 11. Fenêtres, options et fermeture

Créer plusieurs figures : fenêtres distinctes devant BactoMate. Redimensionner/
exporter l’une sans modifier les autres. Le canevas remplit la fenêtre ; export
carré par défaut. Changer ordre/couleur/libellés, espacement/largeur des boîtes,
axes, polices, légende/grille, échelle couleur et dimensions cm/pixels. Contrôler
la taille exportée.

Éditer une figure de longueur avec Figure guide vers largeur : vérifier le nouveau
libellé Y. Rééditer une ancienne fenêtre et vérifier qu’elle retrouve ses propres
choix. Export : PDF/SVG, tables, métadonnées/manifest et scripts, sans PNG automatique.
Croix d’une nouvelle figure : tester Cancel/Discard/Save et annulation du dossier.
Une figure déjà exportée sans changement peut fermer directement. Échap garde ouvert.

## 12. Audit et reproduction

File → Inspect generated files : lire les rôles/copies et sauver éventuellement le
rapport JSON. Aucune suppression. Les nouveaux runs ne doivent plus ajouter de
PNG automatiques ; les anciens restent présents. Un PNG manuel reste possible.

Exécuter reproduce.py depuis son dossier avec Python, NumPy, pandas et Matplotlib.
Vérifier aussi R/MATLAB localement si utilisés. Comparer géométrie/libellés/couleurs,
avec différences de polices possibles. Les scripts ne refont pas la segmentation.

Noter réussite/échec, entrées/XY/frame/canal, étapes, attendu/observé et logs. Garder
sources, curation, presets et bundle fautif. Dernière suite de code enregistrée :
**644 réussis / 5 ignorés** sous Linux le 5 novembre (deux avertissements
existants), dont la réouverture d’un masque remplacé, des verrous Windows
simulés, les grandes polices et des cycles attaché/détaché en zone contrainte,
ainsi que la nouvelle page Analysis, sa table optionnelle et les pixels des contours. L’inférence CPU de l’installateur réussit aux diamètres 30 et 33 le 3 novembre.
Cela ne remplace pas les tests natifs Mac/Windows ni l’évaluation biologique.

## 13. Comparaison de référence Mac/Windows — 3 novembre 2026

Mettre à jour les sources puis relancer l’installateur pour appliquer les versions
communes. Garder/renommer un éventuel venv.previous avant une nouvelle installation.
Vérifier le contrôle des versions et les vraies inférences CPU de l’installation.
Sur le même TIFF phase, modèle et paramètres, décocher Use GPU des deux côtés et
faire Re-detect. Comparer empreintes pixels/poids, versions, moteur effectif,
paramètres et éventuelle reprise avant les comptes aperçu/export.

Tester le diamètre 33 : une reprise doit conserver dimensions/diamètre et être
enregistrée. Un échec persistant doit arrêter sans nouveau masque vide ni fausse
réussite. Fermer/rouvrir l’aperçu puis changer les champs : aucune erreur de
QDoubleSpinBox détruit. Clear Cache doit invalider les aperçus disque. Les comptes
historiques d’exports sans tuilage peuvent changer avec le nouveau calcul commun.
Voir [la procédure détaillée en anglais](docs/MAC_WINDOWS_REPRODUCIBILITY.md).

## 14. Segmentation vers Filtering après relance — 4 novembre 2026

Relancer la segmentation sur un masque déjà édité, puis ouvrir Filtering. Le
nouveau masque doit apparaître sans « Cannot restore mask state ». L’ancien JSON
est conservé dans `curation_archive/` ; les paramètres de filtres cellule/foci et
la calibration restent, mais les anciens choix manuels, contours ajoutés et
historiques ne sont pas appliqués aux nouveaux objets. Avec les nouveaux fichiers
de curation, une réécriture identique des pixels avec d’autres métadonnées TIFF
conserve les choix. Un ancien fichier dont le TIFF a déjà changé est archivé
par précaution. Cette reprise ne modifie pas le TIFF des masques.
Le `.curation.json` conserve l’état ; le `.tmp` sert à l’écriture temporaire.
Les verrous Windows sont réessayés ; un échec nettoie son fichier temporaire et
garde le dernier JSON valide. Seuls les temporaires propres à ce masque, vieux
de plus de 24 heures, sont nettoyés à l’ouverture. Voir le
[guide anglais](docs/FILTERING_CURATION.md).

## 16. Contours identiques et Analysis sur toute la largeur — 5 novembre 2026

Comparer le même masque de 1608 px dans Segmentation et Filtering, avec un zoom
et une couleur identiques : les contours restent d’un pixel, même sur les petits
objets. Segmentation ne les trace plus sur une image réduite à 1024 px. Détection
et masques scientifiques restent inchangés. Tester attaché et détaché.

Analysis conserve Conditions & replicates et Figure guide en haut. Six groupes
avancés se répartissent sur toute la largeur en une à trois colonnes ; les choix
simples et les actions occupent deux groupes. Le tableau et l’espace de figure
vides n’occupent plus la page. **Show data table** ouvre les valeurs en lecture
seule dans une fenêtre séparée, avec toutes les lignes. Vérifier les lignes après
100, le choix d’une table à inspecter sans changer les paramètres de figure,
fermeture/décochage/réouverture et remise à zéro de session. Figures, guide, exports
et chargement automatique des résultats doivent continuer à fonctionner.


## 17. Enveloppes VDemo et cartes des cellules courbes — 5 novembre 2026

Dans Figure guide, choisir démographe, canal et population retenue. Garder
Automatic et Length-scaled columns : cellules courtes avant les longues, profils
centrés sur zéro, enveloppe croissante. Y est la distance axiale divisée par la
demi-longueur de la plus longue cellule. Comparer fluorescence et Local cell width
(µm) : la largeur reste physique même après un ancien choix d’intensité normalisée.
Tester les lignes normalisées et l’option native. Comparer `cell_order.csv` aux
colonnes ; les bins manquants doivent rester manquants.

Choisir Map fluorescence on a normalized cell. Comparer fonds noir/blanc, palettes,
intensités et conditions séparées. La capsule moyenne donne le même poids à chaque
cellule contributrice, sans extrapoler hors du support mesuré. Contrôler nombres
dans `cell_coverage.csv`, CSV/XLSX, fond et contours après reproduction Python.
Les grandes tables doivent occuper plusieurs feuilles Excel numérotées sans perte
de lignes ; le CSV reste complet.

Sur une cellule vibrioïde avec foci connus aux pôles, sur l’axe et réellement
latéral, comparer Principal axis et Automatic. Les points axiaux restent près de
l’axe local ; le point latéral garde son décalage. Vérifier x/y bruts et distance
normale physique. Après rotation de 90°, décalages latéraux absolus et distance au
pôle proche doivent être comparables à la précision du pixel. Un masque courbe
branché doit produire une erreur sans coordonnées inventées. Tester lissage/
résolution de densité, points et fonds. Recréer les anciennes figures spatiales
depuis masques/images pour appliquer la correction. Répéter tracé/édition/fermeture
et changement de projet pendant un calcul : aucun résultat périmé ne doit agir sur
un autre projet ou une vue Analysis détruite.

Suite Linux finale : **655 réussis, 5 ignorés**, 18 avertissements de deux types
préexistants. Les tests spatiaux utilisent des positions synthétiques connues aux
pôles/sur le côté et une extraction réelle de 114 cellules, avec figures/exports
inspectés. Mac/Windows natifs et R/MATLAB restent à tester localement ; ces contrôles
logiciels ne valident ni identité des pôles ni précision biologique de localisation.
