# Aperçu des distances de colocalisation

Dans Analyze → Foci analysis, les valeurs initiales sont **Max distance = 3 px**
et **Threshold = 2 px**. Une session déjà enregistrée conserve ses propres valeurs.

**Preview distances…** ouvre l’image et un zoom sur une cellule. Choisir une
cellule dans la liste ou cliquer sur son contour dans la vue d’ensemble. Le menu
Image background permet de passer de la phase à la fluorescence disponible.
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
