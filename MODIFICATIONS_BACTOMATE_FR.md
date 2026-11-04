# BactoMate Custom — bilan consolidé des modifications

Mise à jour : **4 novembre 2026**. Le code de référence du 1 novembre était
**`811d5b6`** ; la section 13 décrit l’harmonisation suivante.
Base : BactoMate **2.9.5**, commit **`2dfd181`**.
Branche active : **BactoMate_Custom_New-Analyses**.
[Version anglaise](MODIFICATIONS_BACTOMATE_EN.md) · [Guide de test](GUIDE_TEST_BACTOMATE_FR.md)

Ce bilan remplace le journal cumulatif précédent et décrit le comportement final.
Les branches V1 et Analyses ont été supprimées de GitHub à ta demande. Le travail
se poursuit sur New-Analyses. Les guides thématiques sont désormais en anglais ;
seuls ce bilan et le guide de test ont aussi une version française.

## 1. Conversion des ND2 multipositions

Toutes les positions XY sont exportées séparément, avec leurs canaux séparés ou
un TIFF multicanal par XY. Les noms multipositions comportent XY001, XY002, etc.
La série temporelle sélectionnée reste dans chaque pile. Calibration, rôles des
canaux, sélection/projection Z, recadrage et corrections restent disponibles.
La reconnaissance du canal phase Nikon PH3 est corrigée. L’aperçu montre le
premier XY ; il faut aussi contrôler les autres positions exportées.

## 2. Segmentation et images détachées

Les cellules sont affichées par contours, de couleur réglable et mémorisée, sans
remplissage masquant leur intérieur. Changer la couleur ne relance pas la détection
et ne modifie pas les labels. Les nouveaux TIFF de contours utilisent ce style ;
les anciens exports ne sont pas réécrits.

L’image se détache en Segmentation et Filtering. Les LUTs la suivent et restent
ouvertes à droite. Les contrastes sont propres aux canaux pendant la navigation ;
Filtering les distingue aussi par masque/XY. Cela ne garantit pas leur conservation
après fermeture complète de l’application. Les LUTs modifient l’affichage, jamais
les pixels ni les mesures sources.

Molette : zoom doux autour du pointeur. Clic gauche maintenu : déplacement.
Recenter/fit et glissières horizontale/verticale : navigation dans l’image.
Échap garde la fenêtre ouverte, sauf pour annuler un tracé manuel en cours.
Le détachement compacte les contrôles en haut ; le rattachement restaure la mise
en page. La croix propose Save / Discard / Cancel. Sauvegarder produit une vue
TIFF/JPEG en RGB, pas un masque scientifique. Annuler la sauvegarde garde la
fenêtre ouverte. Une fermeture réussie réintègre le canevas.

## 3. Filtering : disposition et mesures

Cell filtering et Foci filtering sont des panneaux fixes. Les tables/historiques
laissent dix lignes visibles. Les commandes Import/Save en double à gauche ont
été retirées ; celles au-dessus des filtres restent disponibles. Les commandes
Keep/Exclude/Use filters suivent l’image détachée avec les LUTs.

La table cellulaire indique aire en µm², longueur/largeur en µm et centre X/Y en
pixels. Longueur/largeur sont les axes de l’ellipse équivalente, pas une longueur
de squelette. Changer la calibration actualise ces mesures ; une calibration
invalide ne produit pas de fausses valeurs physiques. Les effectifs concernent
la frame courante. L’historique garde paramètres et variations d’effectif ; il
ne restaure pas automatiquement un état ancien.

## 4. Sélection et annotations manuelles

Dans un canal de foci, le clic sélectionne le focus du canal et sa ligne, pas sa
cellule hôte. Le mode Cells sélectionne les cellules. Un double-clic sur une ligne
cellulaire recentre l’image. Maj-clic ajoute uniquement les objets cliqués.
Delete/Retour arrière exclut la sélection de façon réversible. Apply garde le
canal View courant.

Seules les cellules retenues ont un contour fin, blanc par défaut, de couleur
modifiable. Les cellules rejetées restent dans la table. Les foci détectés ou
annotés sont verts si retenus, rouges si rejetés/exclus. Le marqueur jaune indique
la sélection de travail et ne change pas leur statut.

Le clic droit ouvre Add / keep object, Remove / exclude object et Create new
object here… ; aucune réintégration immédiate. Un nouveau focus est placé au point
cliqué dans le canal courant. En mode Cells, cliquer les sommets d’un polygone et
terminer avec Entrée/double-clic ; Échap annule. Le polygone doit contenir au moins
trois pixels et ne pas recouvrir une cellule existante.

Ces créations sont des annotations, pas des détections automatiques. Elles passent
dans les tables et exports filtrés ; les foci manuels portent `manual` dans le CSV.
Les sources ne sont pas écrasées. Keep force la conservation, Exclude force le
rejet, Use filters retire le choix manuel. Curation et recettes sont dans le
`.curation.json` du masque, par frame et canal. Un masque source modifié ne reçoit
pas silencieusement les anciens choix sur ses nouveaux labels.

## 5. Réglages par XY/canal et filtrage de lot

Mask / XY position recharge masque, images, tables, foci et curation. Chaque XY
garde ses filtres cellulaires, sa calibration et les filtres propres à chaque
canal. Un XY jamais visité reprend les derniers réglages comme point de départ ;
ensuite ses changements sont indépendants. Changer de canal conserve ses valeurs,
même sans Apply préalable.

Les nouvelles recettes Filtering cochent Exclude cells at borders et Exclude
fully outside. Les choix explicitement enregistrés restent respectés. Les contrôles
Analyze/CLI indépendants peuvent avoir d’autres défauts : vérifier l’étape utilisée.

Filter File/Folder retrouve la liste complète des masques et l’état des résultats,
même après navigation vers un XY isolé. Les variantes brute/filtrée d’un masque
sont regroupées ; la source brute est privilégiée lorsqu’elle existe pour permettre
la réintégration. Chaque masque exporte sa propre recette.

Save filter settings produit un JSON cellules et un JSON par canal nommé, aussi
présents près des masques filtrés exportés. Importer GFP laisse mCherry/cellules
inchangés. Les anciens presets groupés restent importables ; les fichiers invalides
sont refusés. Les presets transportent les filtres, pas les décisions sur objets.

## 6. Aperçu des distances et colocalisation

Défauts : Max distance **3 px**, Threshold **2 px**. Max distance limite les
partenaires candidats ; un appariement un-à-un choisit les paires ; Threshold
classe leur distance centre-à-centre. Same cell only est pris en compte et les
(?) expliquent les paramètres. Une ancienne session peut garder d’autres valeurs.

L’aperçu choisit XY, frame, cellule et canaux. Des cases visibles permettent de
superposer plusieurs fonds. LUT channel choisit l’histogramme à régler sans
réinitialiser les autres. Glisser déplace ; la molette zoome d’environ 5 % par
événement ; les boutons précédent/suivant et les flèches clavier changent de
cellule. Les icônes Home/Pan inutiles ont été retirées.

Le titre de cellule affiche Colocalized ou Not Colocalized selon les paires
valides impliquant cette cellule. Centres cyan/magenta, rayons jaune/vert et
liaisons vertes/orange montrent les décisions. Grille pixel, référence 1 px et
calibration aident la lecture. L’aperçu utilise la logique d’Analyze, actualise
ses paramètres et n’écrit pas de résultats. Sans CSV détecté, il affiche une
information et n’invente pas de foci.

## 7. Session et transfert automatique vers Analysis

Clear current session à l’accueil/menu File ferme aperçus/figures, vide chemins,
caches et attributions en mémoire et revient à l’accueil. Terminer/annuler les
calculs d’abord. Les fichiers et `analysis_groups.json` enregistrés restent sur disque.

Après Analyze réussi, les résultats finaux et fusionnés sont chargés, puis Analysis
s’ouvre automatiquement, pour un fichier ou plusieurs sous-dossiers. La recherche
retrouve `_analysis` depuis les masques segmentés/filtrés. Refresh results relit
les changements et signale les fichiers illisibles. Les copies CSV/XLSX connues,
agrégats redondants et bundles de figures sont évités par les règles du catalogue ;
ce n’est pas une déduplication universelle de fichiers renommés arbitrairement.

## 8. Analysis simplifié, entièrement en anglais

Le mode simple choisit population, figure, mesure et frame. Conditions & replicates
reste en haut dans les deux modes. Le tableau attribue condition et réplicat par
fichier, permet des changements par lot et conserve les choix dans
`analysis_groups.json`. Les XY d’un même réplicat partagent son nom ; le logiciel
ne déduit pas un réplicat biologique du nom d’un XY.

Les distributions cellulaires et moyennes colorées des réplicats sont distinctes.
L’export donne effectif/moyenne/écart-type des réplicats. La première frame évite
un mélange temporel implicite ; All frames signifie observations répétées.
Aucun test statistique ou modèle hiérarchique n’est ajouté automatiquement.

Figure guide : question, population, apparence, récapitulatif/tracé. Le mode
Advanced / MicrobeJ-style controls conserve imports, axes, groupes et filtres
libres. Il s’inspire de MicrobeJ mais n’exécute pas le plugin Fiji. Cellules, foci,
profils, tracking et résumés restent des populations distinctes.

## 9. Figures et profils spatiaux

Treize types : Histogram, Scatter, Mean curve, Box plot, Violin plot, ECDF,
Correlation, Demograph, Kymograph, Normalized cell heatmap, Heatmap, Maxima map,
Foci count. Les métriques numériques compatibles restent accessibles.

Les vues spatiales retrouvent masques/canaux du projet, préfèrent les masques
filtrés et signalent les non filtrés. Calibration depuis les métadonnées ou valeur
explicite. Principal axis convient aux bâtonnets droits ; Medial axis suit un
squelette pixel de cellule courbe et refuse les axes ambigus. Coordonnées et
métriques brutes restent exportables. L’orientation géométrique ne donne pas l’âge
des pôles ; Bright pole place explicitement le plus lumineux à gauche/en haut.

Démographe : une ligne par observation cellulaire, tri par longueur, axe 0–1.
Défaut **24 segments longitudinaux**, sans changer les paramètres du réseau de
segmentation cellulaire. Native resolution → 24 positions mesure à environ un
pixel d’intervalle, puis interpole linéairement sur la grille commune ; les bords
reprennent la première/dernière moyenne mesurée. `native_profiles.csv` conserve
les mesures natives. L’interpolation n’augmente pas la résolution optique.

Intensité brute, division par maximum cellulaire et min–max sont des choix explicites.
Les bins directs vides restent manquants, pas zéro ; une cellule constante devient
0 en min–max. Maxima map distingue pixel le plus brillant et foci conservés. Sa
densité relative et sa capsule schématique ne mesurent pas l’intensité ni un contour
moyen réel. Foci count utilise les cellules avec zéro focus dans le dénominateur.

Kymographe : un XY/canal, au moins deux frames, une identité cellulaire suivie et
vérifiée. Le guide retrouve les masques Tracking ; des labels ordinaires exigent
une confirmation de continuité. Axe temporel en minutes si l’intervalle est connu,
sinon en frames. Aucun tracking ou âge de pôle n’est inventé.

## 10. Fenêtres, options et exports des figures

Chaque figure a sa fenêtre libre, affichée devant BactoMate, ses données et ses
options. Le canevas remplit la fenêtre ; l’export travaille hors écran sans changer
les autres vues. Page carrée par défaut **15,24 × 15,24 cm** ; dimensions réglables
en cm ou pixels, avec conversion DPI. La capsule garde un rapport interne adapté.

Figure options : ordre/libellés/couleurs des catégories, espacement/largeur des
boîtes/violons, axes/limites, rotation, polices, marqueurs/opacité, traits, outliers,
légende/grille/titre, échelle couleur, dimensions/DPI. Edit with Figure guide reprend
la recette de la bonne fenêtre. Changer de métrique retire les anciens libellés
surchargés : largeur ne garde plus le libellé longueur.

Échap laisse la figure ouverte. La croix demande Save / Discard / Cancel si la
figure est nouvelle/modifiée ; une figure déjà exportée sans changement se ferme
directement. Annuler l’export garde la fenêtre ouverte. Le reset interne ferme les
figures sans dialogue individuel.

Les bundles exportent PDF/SVG, CSV/XLSX des sources/valeurs tracées, métadonnées,
manifest SHA-256 et scripts Python/R/MATLAB. Tables réplicats/profils natifs selon
le cas. Les scripts redessinent la géométrie enregistrée, sans refaire la détection.
Polices/rendu peuvent varier. Python est exécuté dans les tests ; R/MATLAB restent
à contrôler dans leurs logiciels.

## 11. Fichiers générés et audit

Les PNG automatiques de résultats sont désactivés, y compris les écritures
redondantes de Filtering. Figures/scripts produisent PDF/SVG par défaut. Un PNG
explicitement demandé reste possible via les outils manuels/API. Les anciens PNG
ne sont pas supprimés en masse. Masques, TIFF de contrôle et tables sont conservés.

File → Inspect generated files fait un audit en lecture seule : rôles, contenus
identiques, copies CSV/XLSX, rapport JSON enregistrable. Aucune suppression.
Masques bruts/filtrés et classeurs individuels/agrégés ont des usages différents.
Also save CSV est décoché par défaut ; le cocher crée volontairement une copie texte.

## 12. Validation et limites

Dernière suite complète enregistrée : **614 tests réussis, 5 ignorés**, puis
**11 contrôles ciblés réussis** après les dernières retouches, dont sauvegarde
TIFF réelle et statut de colocalisation. La réécriture des docs ne prétend pas
constituer une nouvelle exécution complète de l’application.

Les essais réels précédents ont vérifié neuf TIFF d’un ND2 à trois XY/trois canaux,
un seul temps, avec égalité des pixels et calibration ; contours sur les trois XY ;
curation/export et démographe GFP de 144 cellules sur XY001. Films ND2 réels,
justesse biologique foci/colocalisation, comportement macOS natif et exécution
native R/MATLAB restent à évaluer localement. Les tests de code ne certifient pas
la validité scientifique de nouvelles données.

## 13. Harmonisation Mac/Windows — 3 novembre 2026

Les versions du socle de segmentation/lecture sont fixées à l’identique, dont
DBSCAN 0.0.12. Les outils CUDA conservent les versions imposées de torch/vision/audio.
Windows recrée le venv en protégeant l’ancien ; les deux installateurs vérifient
les versions et font une vraie inférence CPU aux diamètres 30/33 avant réussite.

Aperçus simples/dossier et exports Omnipose utilisent le même calcul natif avec
tuilage. L’aperçu ne force plus le GPU : Use GPU est respecté et visible dans les
contrôles intégrés. Le CPU sert de référence de comparaison ; les réglages cuDNN
privilégient la stabilité, sans benchmarking/TF32. L’erreur de taille au diamètre
33 est reprise avec rééchantillonnage sur grille native, sans recadrer l’image
ni changer le diamètre, et ce choix est enregistré. Un échec persistant interrompt
le run au lieu d’enregistrer un masque vide et d’annoncer une réussite. Les
contrôles d’aperçu se déconnectent à leur destruction. Les caches incluent pixels,
poids et versions ; Clear Cache retire aussi les entrées disque du fichier courant.

Logs/sessions enregistrent environnement, moteur réel, paramètres et empreintes
des pixels/poids/résultats, sans nouveaux fichiers de diagnostic par image ni PNG.
L’alignement du tuilage peut changer les anciens comptes des exports : il ne force
pas le résultat historique de 464 cellules. Le TIFF réel de validation antérieur
a été traité localement sur CPU aux diamètres 30 et 33 ; l’erreur exacte d’un pixel
a été reproduite puis reprise. Les essais natifs Mac/Windows restent nécessaires.
Voir [le guide anglais de comparaison](docs/MAC_WINDOWS_REPRODUCIBILITY.md).

Les empreintes des modèles phase/fluorescence intégrés sont vérifiées au chargement.
Une copie différente est signalée sans suppression ; restaurer celle livrée avec
la branche, ou charger les autres poids explicitement comme modèle utilisateur.

Validation du 3 novembre : **626 tests réussis, 5 ignorés** dans la suite complète
sous Linux, avec deux avertissements existants ; l’inférence CPU de l’installateur
réussit aux deux diamètres. Les essais natifs macOS/Windows restent à faire.

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

Validation du 4 novembre : **636 tests réussis, 5 ignorés** sous Linux (deux
avertissements existants), dont la réouverture Qt avec une ancienne curation,
les archives, les choix conservés à pixels identiques, la protection d’un éditeur
périmé et des verrous Windows simulés. L’essai Windows natif reste à faire.
