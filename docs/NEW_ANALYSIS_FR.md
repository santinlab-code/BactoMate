# Analysis : un parcours simple

Cette interface est développée uniquement sur **BactoMate_Custom_New-Analyses**.
Les branches BactoMate_Custom_Analyses et BactoMate_Custom_V1 restent inchangées.

## Exemple : aire cellulaire, conditions X et Y, avec réplicats

1. Faire les mesures dans Segmentation → Analyze comme d’habitude. Ouvrir ensuite
   **Analysis**. Les résultats du projet sont trouvés et lus automatiquement.
2. Garder **Cellules**, choisir **Violon**, puis **Aire cellulaire (µm²)**.
3. Ouvrir **Conditions et réplicats…**. Attribuer X ou Y et le nom du réplicat
   biologique à chaque fichier. Plusieurs lignes peuvent recevoir le même choix
   avec **Appliquer aux lignes choisies**. Plusieurs positions XY d’une même
   expérience peuvent partager un même réplicat. Enregistrer une fois : ces choix
   sont gardés pour les prochaines ouvertures du projet.
4. Garder **Comparer les conditions** et **Afficher les moyennes des réplicats**,
   puis cliquer sur **Créer la figure**. Chaque violon représente les observations
   cellulaires d’une condition ; chaque point coloré représente la moyenne d’un
   réplicat. Un même réplicat conserve sa couleur entre conditions.
5. **Exporter figure, tableur et code…** garde les exports PNG/PDF/SVG, CSV, Excel
   et les scripts Python/R/MATLAB. Une feuille **Replicates** et un CSV dédié donnent
   les effectifs, moyennes et écarts-types de chaque réplicat par condition.

Pour un film, choisir une frame avec **Temps / frame**. Si plusieurs frames existent,
la première est choisie par défaut. Le choix **Toutes** regroupe les observations :
une même cellule suivie peut alors apparaître plusieurs fois. Les effectifs ne sont
pas présentés comme autant de cellules indépendantes ou de réplicats biologiques.

## Quelles données sont prises en compte ?

Le dossier du projet ouvert dans le Dashboard est utilisé. Si aucun projet n’est
ouvert, le chemin déjà choisi dans Analyze, Filtering ou Tracking sert de point
de départ. Il n’y a pas de dialogue pour charger des tableurs dans le parcours simple.
Si aucun contexte n’existe, l’interface explique comment ouvrir le dossier du projet.

Les répertoires d’analyses et de tracking sont parcourus, ainsi que les fichiers
nommés comme des résultats d’analyse. CSV, TSV, XLSX et XLSM sont reconnus. Cellules,
foci, suivi, profils et résumés restent des populations distinctes. Les résumés ne
sont pas mélangés avec les lignes individuelles. Les exports de figures ne sont
pas réimportés ; les doubles XLSX/CSV connus et les classeurs master/combined sont
écartés lorsque les résultats individuels existent. Les fichiers illisibles sont
signalés dans le panneau. Les formats non pris en charge ne sont pas convertis.

La recherche se fait à l’entrée dans la section et avec **Actualiser les résultats**.
Les fichiers inchangés sont gardés en cache ; les résultats modifiés sont relus.
Le changement de projet vide les anciennes données pour éviter de les mélanger.

## Conditions et réplicats

Aucun réplicat biologique n’est deviné à partir d’un nom de fichier ou d’une position
XY. Le petit tableau d’attribution est prévu pour les définir. Les valeurs sont
stockées dans **analysis_groups.json**, dans le dossier du projet ; les résultats
sources ne sont pas modifiés.

Si les tables possèdent déjà des colonnes condition/replicate, elles sont reprises.
Une attribution non vide dans le tableau remplace ces valeurs pour le fichier.
Une attribution vide conserve celles du tableur. Sans information suffisante,
l’interface demande de compléter les attributions avant de comparer les groupes.
Les moyennes des réplicats sont calculées sur les observations sélectionnées de
chaque paire condition–réplicat, en réunissant leurs fichiers/XY. Aucun test de
significativité ou modèle statistique hiérarchique n’est ajouté implicitement.

## Les autres figures

Le mode simple couvre les violons, boîtes, histogrammes, répartitions, nuages de
points et courbes moyennes. **Réglages avancés** garde les onze figures, le choix
libre des axes et groupes, les filtres, les profils, les démographes, kymographes et
cartes normalisées. Choisir une vue spatiale ouvre ce mode. Les prérequis décrits
dans [ANALYSIS_FR.md](ANALYSIS_FR.md) restent valables : aucune trajectoire ou donnée
spatiale manquante n’est inventée. Les extractions de profils restent disponibles
avec les images/masques appropriés dans ce mode avancé.

Les données de la figure sont conservées dans l’export. Les scripts redessinent
la géométrie calculée pour préserver les mêmes distributions et moyennes ; les
moteurs peuvent différer pour les polices et dimensions. Python est testé par
exécution. L’exécution native des scripts R/MATLAB et le rendu Mac restent à vérifier.

Après un calcul Analyze réussi, BactoMate charge les résultats puis ouvre
Analysis automatiquement. Aucun fichier à importer, ni fenêtre « OK » à fermer.
Depuis l’accueil, Clear current session vide les données et chemins en mémoire
pour commencer un autre jeu de données. Les résultats et attributions enregistrés
sur disque sont conservés.
