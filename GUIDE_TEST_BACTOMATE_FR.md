# Tester la version de travail BactoMate

## Télécharger la version de test

Version du 28 octobre 2026 : télécharger la branche **BactoMate_Custom_New-Analyses** :
https://github.com/santinlab-code/BactoMate/archive/refs/heads/BactoMate_Custom_New-Analyses.zip

Extraire le ZIP dans un nouveau dossier, puis suivre les étapes Windows ou macOS
ci-dessous. Ce ZIP contient les sources ; les applications de la release officielle
ne contiennent pas ces ajouts. Le résumé est dans MODIFICATIONS_BACTOMATE_FR.md.

## Quelle version installer ?

L’archive `BactoMate-version-test.zip` contient le code actuel et les modifications
décrites dans `MODIFICATIONS_BACTOMATE_FR.md`. C’est une archive de sources avec
les scripts d’installation, pas une application Windows ou macOS déjà compilée.
Les applications proposées par la release officielle ne contiennent pas ces
changements.

Extraire l’archive dans un nouveau dossier, par exemple `BactoMate-test` dans
Documents. Ne pas remplacer votre installation habituelle. L’archive ne contient
pas votre fichier ND2 ni les résultats des essais effectués ici.

## Windows

Prérequis du projet : Windows 10/11 en 64 bits, Python **3.11 en 64 bits** de
python.org (éviter Conda et le Python Microsoft Store) et Microsoft Visual C++
Redistributable en 64 bits. À l’installation de Python, cocher l’ajout au PATH.

1. Extraire complètement l’archive dans Documents.
2. Ouvrir le dossier extrait qui contient `main.py` et `requirements.txt`.
3. Double-cliquer sur `install_windows.bat` et laisser l’installation se terminer.
4. Double-cliquer sur `launch_windows.bat` pour démarrer cette version.

Si Windows bloque l’archive téléchargée, ouvrir ses Propriétés et utiliser
Débloquer, si cette option est proposée, puis extraire à nouveau.
Le guide détaillé du projet est `docs/INSTALL_AND_LAUNCH_windows.md`.

## macOS

Prérequis du projet : macOS 10.15 ou plus récent et Python **3.11**.
L’installation à partir des sources demande quelques commandes dans Terminal.
Ouvrir Terminal (Applications → Utilitaires). Taper `cd` suivi d’un espace,
puis glisser le dossier extrait contenant `main.py` dans la fenêtre du Terminal
et appuyer sur Entrée. Exécuter ensuite les deux lignes suivantes, l’une après l’autre :

```bash
chmod +x setup/macos/*.sh launch_gui.sh
./setup/macos/install.sh
```

L’installateur télécharge les bibliothèques nécessaires ; la première installation
peut prendre plusieurs minutes. En cas d’erreur, transmettre le message affiché
avant de tenter de modifier Python. Cette archive a été vérifiée dans notre
environnement Linux ; son installation et son interface sur votre Mac restent
à confirmer par cet essai.

Pour démarrer ensuite, dans le même dossier :

```bash
./launch_gui.sh
```

## Linux

L’environnement cloud utilisé pour les essais est Linux avec Python 3.11.
Les procédures destinées aux utilisateurs du projet concernent surtout Windows
et macOS. Pour une installation Linux locale, préciser la distribution afin
d’adapter les dépendances graphiques et l’installation.

## Parcours d’essai sur le fichier de référence

Utiliser une copie du ND2 et un nouveau dossier de résultats pour ces essais.

### A. Conversion

1. Choisir le fichier ND2 dans File Conversion.
2. Attribuer le rôle Phase au canal PH3.
3. Cocher Fluorescence et Foci pour GFP et mCherry.
4. Convertir les trois positions et les trois canaux.
5. Vérifier la présence de neuf TIFF, avec XY001, XY002 et XY003.

### B. Segmentation

1. Segmenter les images de phase avec le modèle habituel de l’équipe.
2. Ouvrir l’aperçu : vérifier que les contours laissent voir les cellules.
3. Changer la couleur avec Outline color… et vérifier le résultat.

### C. Filtering et curation

L’image s’ouvre séparément : la déplacer sur le deuxième écran si souhaité.
Choisir Cells ou Foci dans cette fenêtre, cliquer sur un objet et vérifier
le cadre jaune et la ligne sélectionnée dans la table. Appuyer sur Supprimer
ou Retour arrière pour l’exclure, puis le réintégrer avec Keep selected objects.
Fermer la fenêtre d’image pour la réintégrer ; Detach image la détache à nouveau.

1. Ouvrir Preview filters et le panneau Cell table / Manual selection / History.
2. Noter le nombre initial de cellules ; appliquer un filtre de taille.
3. Vérifier le nouveau nombre et les critères dans l’historique.
4. Sélectionner une cellule dans la table et utiliser Exclude selected objects.
5. La réintégrer avec Keep selected objects.
6. Utiliser Use filters for selected objects pour revenir au choix automatique.
7. Exporter avec Filter File/Folder et vérifier le masque filtré.

### D. Indépendance des canaux et paramètres

1. Dans View, choisir GFP et fixer un seuil de filtrage reconnaissable.
2. Passer sur mCherry et saisir un seuil différent.
3. Revenir sur GFP : vérifier que sa valeur et ses cases cochées sont conservées.
4. Exporter : rechercher le JSON des cellules et les deux JSON des foci.
5. Changer les réglages GFP, puis importer uniquement le JSON GFP.
6. Vérifier que GFP est restauré, sans changement pour mCherry ni les cellules.

Les tests de sélection de foci nécessitent les CSV produits par leur détection.
Si aucun focus n’a encore été détecté, effectuer cette détection avant l’essai.

### E. Aperçu de colocalisation

1. Dans Analyze → Foci analysis, vérifier 3 px pour Max distance et 2 px pour
   Threshold (sauf si une session enregistrée a chargé d’autres valeurs).
2. Ouvrir Preview distances… et cliquer sur une cellule.
3. Choisir GFP et mCherry pour A et B, puis le fond phase ou fluorescence.
4. Vérifier la grille et le repère 1 px dans le zoom.
5. Sur une cellule contenant des foci détectés, modifier les deux distances et
   observer les cercles et les paires affichées.
6. Vérifier que les valeurs de Foci analysis suivent les changements de l’aperçu.

## Comment signaler un problème

Indiquer la section utilisée, ce que vous avez fait, ce que vous attendiez et
ce qui s’est produit. Ajouter le nom du fichier, la position XY, le canal et
la frame concernés, ainsi que le message d’erreur exact ou une capture d’écran.
En cas d’échec d’installation, transmettre le journal `Logs/install.log` sur Mac,
ou `Logs/install_last.log` sur Windows, si ce fichier a été créé.

La fenêtre peut toujours afficher le numéro de base **2.9.5** : aucun nouveau
numéro de release officiel n’a été attribué. Le bouton Preview distances…
et les boutons d’import/export de Filtering permettent de reconnaître cette version.

## Nouvelle section Analysis

Depuis le Dashboard, ouvrir Analysis pour charger les résultats CSV/Excel,
choisir les métriques, tracer et exporter les figures. Le guide détaillé des
profils, démographes, kymographes et scripts est `docs/ANALYSIS_FR.md`.
La branche BactoMate_Custom_V1 reste la copie de secours.

## Analysis simplifiée

Les résultats du projet sont désormais repris automatiquement. Pour un violon
d’aire selon les conditions et réplicats, suivre `docs/NEW_ANALYSIS_FR.md`.
L’interface avancée reste disponible. Les branches Analyses et V1 sont conservées.
