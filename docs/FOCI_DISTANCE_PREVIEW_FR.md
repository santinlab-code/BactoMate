# Aperçu des distances de colocalisation

Dans Analyze → Foci analysis, les valeurs initiales sont **Max distance = 3 px**
et **Threshold = 2 px**. Une session déjà enregistrée conserve ses propres valeurs.

**Preview distances…** ouvre l’image et un zoom sur une cellule. Choisir une
cellule dans la liste ou cliquer sur son contour dans la vue d’ensemble. Les boutons ← Cell et Cell → (ou les touches fléchées) passent à la cellule
précédente ou suivante. Les cases à cocher visibles pour chaque image permettent de superposer
la phase et plusieurs canaux de fluorescence disponibles. Les couleurs des
images sont indépendantes des marqueurs A/B.
Les menus A et B choisissent les deux canaux à comparer ; Frame sélectionne le
temps dans un film.

Les centres des foci sont cyan et magenta. Autour des foci A de la cellule choisie,
le cercle jaune pointillé représente le rayon de recherche Max distance et le
cercle vert le seuil Threshold. Ce sont des distances centre à centre, pas une
mesure du diamètre du focus. La grille du zoom marque les bords des pixels
(pour les zooms de moins de 160 pixels). Un carré blanc indique 1 pixel ; la
calibration en µm est affichée si disponible.

Une ligne verte relie une paire comptée comme colocalisée ; une ligne orange
indique une paire appariée mais au-dessus du seuil. L’aperçu utilise le même
appariement un-à-un et l’option Same cell only que l’analyse. Les effectifs affichés
concernent la frame entière. Les modifications mettent à jour les champs de
Foci analysis, sans écrire de résultats ni relancer la détection.

Les masques et CSV filtrés sont utilisés si l’option correspondante est cochée,
comme pour l’analyse. Sans CSV de détection, les images et les cellules restent
visibles, avec un message indiquant l’absence de foci détectés ; aucun focus
artificiel n’est ajouté. Effectuer d’abord la détection pour comparer les paires.


Le menu **Mask / XY position** choisit la segmentation à observer parmi celles du
chemin d’analyse. Une position est affichée à la fois. Changer de masque recharge
ses images, ses cellules, ses canaux, ses détections et sa calibration ; les
positions XY ne sont pas superposées.

**LUT channel** choisit l’image à régler, même si elle est masquée. L’histogramme interactif est le même que dans Segmentation/Filtering : déplacer
les lignes Min/Max pour régler le contraste du canal choisi. Auto LUT utilise les
percentiles 1 et 99,5 de la frame courante. Chaque image garde sa propre LUT
pendant l’observation de cette position. Les canaux cochés sont additionnés puis
bornés pour l’affichage. Ces réglages ne changent ni les pixels sources, ni les
mesures, ni l’appariement.

La molette zoome et dézoome autour du pointeur dans chacune des deux vues.
Maintenir le clic gauche et glisser déplace directement l’image, dans les deux vues.
Un clic simple dans la vue d’ensemble choisit toujours la cellule.
Les icônes Maison et déplacement ont été retirées. Changer de cellule recentre le zoom ; changer
une LUT ou un seuil conserve la zone observée. Le bouton Zoom n’est plus requis.
Les petits **(?)** près de Max distance et Threshold expliquent le rayon de
recherche et le seuil de colocalisation.

Le zoom à la molette progresse par environ 5 % au maximum par événement,
pour permettre un réglage plus fin, notamment au pavé tactile.

Les images disponibles (phase et canaux) sont proposées sous forme de cases à
cocher directement visibles, sans menu déroulant. Plusieurs cases peuvent être
cochées pour superposer les images. Le menu LUT channel choisit seulement la LUT
à régler ; changer ce choix conserve les contrastes propres aux autres canaux.
