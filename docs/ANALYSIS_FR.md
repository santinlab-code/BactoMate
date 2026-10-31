# Analysis — figures et profils quantitatifs

Cette section indépendante est disponible dans le Dashboard et la navigation.
Elle est développée uniquement sur `BactoMate_Custom_Analyses`.
`BactoMate_Custom_V1` reste au commit `7e92cd7`.

## Référence MicrobeJ et choix de méthode

Le point de départ est la représentation des métriques et profils décrite dans
[Ducret et al., MicrobeJ (2016)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5010025/) :
tables de propriétés, profils orientés, démographes triés et vues temporelles.
La documentation officielle des résultats est à
https://www.microbej.com/doc/ResultsInterface.html (indisponible lors de la lecture).

Ce module est une implémentation BactoMate ; il n’exécute pas le plugin MicrobeJ.
Il ne reprend pas ses contours sous-pixel, ses règles de polarité biologique,
son clustering ou tous ses outils interactifs. Les méthodes sont indiquées dans
les exports pour ne pas confondre les mesures des deux logiciels.

## Tables et graphiques

Load tables accepte CSV, TSV et XLSX/XLSM. Toutes les feuilles Excel sont
accessibles séparément : cellules, foci, résumés, tracking, etc. Tous les champs
numériques peuvent servir de métriques ; les champs texte servent aux groupes.
Plusieurs tables ayant les mêmes colonnes peuvent être choisies dans une table
Pooled, avec une colonne source_table conservant la provenance. Cette table est
une option explicite et ne remplace pas les tables individuelles.

Les 11 vues sont : histogramme, nuage de points, courbe moyenne, boîte, violon,
fonction de répartition cumulée, corrélation, démographe, kymographe, carte de
cellule normalisée et heatmap générale.

Choisir X, Y, Value selon la figure, puis éventuellement Group, filtre exact et
bornes X. Histogram utilise des bornes communes aux groupes. Mean curve calcule
la moyenne par groupe et valeur X, sans inférence statistique ni erreur standard.
Les cellules ne sont pas automatiquement considérées comme réplicats biologiques.
Correlation utilise Pearson sur les colonnes numériques, par paires, avec au moins
trois observations. Les colonnes ID numériques figurent aussi dans cette vue :
préparer une table ne contenant que les métriques souhaitées si nécessaire.
Le violon utilise la KDE Matplotlib ; les groupes constants restent des points.

La prévisualisation du tableur montre les 100 premières lignes. Les calculs utilisent
les lignes sélectionnées complètes, sans échantillonnage. Après un changement de
réglage, redessiner avant d’exporter. L’outil garde un instantané des données et
réglages ayant produit la figure.

## Profils et cartes normalisées

Build profiles demande un masque TIFF à labels entiers et un TIFF de fluorescence
pour un seul canal et une seule position XY. Les dimensions TYX doivent correspondre.
Utiliser les masques filtrés pour limiter l’étude aux cellules retenues. Indiquer
la calibration µm/px avant extraction. L’extraction tourne hors du fil graphique.

Deux tables sont créées : Cells (une ligne par cellule/frame) et Spatial profiles.
Cette dernière contient des profils longitudinaux et des cartes 2D séparés.
Le type de figure choisit le bon sous-ensemble. Positions longitudinales et
transversales sont normalisées entre −1 et +1 ; intensité et nombre de pixels
contributeurs sont conservés. Une case vide reste manquante, jamais remplacée
par une valeur zéro ni interpolée artificiellement.

Medial axis suit un squelette à résolution pixel et projette chaque pixel vers
son point central le plus proche. Les distances cumulées suivent les courbures.
Les axes ramifiés, cycliques ou trop courts sont refusés avec le numéro de cellule.
Principal axis est une projection droite par PCA, disponible comme autre méthode ;
elle ne redresse pas les cellules courbes. Les longueurs et largeurs de la table
Cells restent les axes de l’ellipse équivalente, avec leur calibration.

Geometric fixe l’orientation par les coordonnées de l’image. Bright pole place
le pôle le plus lumineux du côté positif ; ce choix peut modifier la moyenne de
population. Aucune de ces orientations ne détermine l’âge des pôles.
Map intensity offre raw, per-cell max et per-cell min-max. Les valeurs brutes sont
conservées dans une colonne séparée lorsqu’une normalisation est appliquée.
Les cellules constantes deviennent zéro en min-max. Les choix sont enregistrés.

Pour un démographe : Spatial profiles, X=position, Y=object_key, Value=intensity,
Sort=length_um. Le tri est stable. L’identité complète est conservée dans les données ;
les longues étiquettes sont raccourcies sur la figure.
Pour une carte moyenne normalisée : X=position, Y=transverse, Value=intensity.
Chaque cellule contribue par sa moyenne de case occupée, sans pondération par sa
surface. Filtrer la frame pour éviter de mélanger un instantané et un film.

Un kymographe exige des identités suivies et vérifiées. X=position, Y=frame ou temps,
Value=intensity, Group=ID de track. Filtrer un track et une source, puis confirmer
la continuité des identités. Les labels de segmentation ne sont **pas** des tracks
par défaut. Le module ne fait aucun appariement temporel implicite.

## Export et reproduction

Export crée un nouveau dossier horodaté avec :

- figure.png (300 dpi), figure.pdf et figure.svg ;
- figure_data.xlsx, source_rows.csv et plot_data.csv : lignes utilisées et valeurs
  réellement tracées, y compris matrices, cases manquantes et effectifs de courbes ;
- figure.json : paramètres et provenance ; manifest.json : empreintes SHA-256 ;
- figure_geometry.csv, axes.json et palette.csv pour les cartes ;
- reproduce.py, reproduce.R et reproduce.m.

Les scripts redessinent les primitives calculées (points, lignes, distributions,
rectangles et couleurs). Ainsi R et MATLAB ne recalculent pas une autre KDE ou
d’autres quartiles. Les données et identités restent disponibles pour refaire
une analyse différente. Le script ne requiert pas BactoMate, mais les polices,
épaisseurs et dimensions peuvent varier entre moteurs.
Python : pandas et matplotlib, puis `python reproduce.py`.
RStudio : ouvrir le dossier comme répertoire de travail, installer jsonlite si
nécessaire, puis exécuter reproduce.R. MATLAB : ouvrir le dossier et exécuter
reproduce.m (version avec jsondecode et exportgraphics).

Les scripts Python sont exécutés dans les tests pour les 11 figures. R et MATLAB
ne sont pas installés dans l’environnement de développement : leur exécution
native reste à vérifier, ainsi que l’interface sur Mac. Une extraction et un
export réels ont été vérifiés sur les 144 cellules de XY001/GFP.
