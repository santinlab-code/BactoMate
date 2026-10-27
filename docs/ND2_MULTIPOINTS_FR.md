# Exporter les positions XY d’un fichier ND2

Dans **File Conversion**, la conversion ND2 exporte automatiquement toutes les
positions XY du fichier. Il n’y a pas de case supplémentaire à cocher.

Avec **Save channels separately** activé, chaque position et chaque canal
produisent un TIFF distinct dans le dossier habituel **Tif_files**, à côté du ND2.
Par exemple, pour trois positions avec un canal Phase et un canal GFP désigné FI :

```text
Tif_files/
  experience_XY001_phase.tif
  experience_XY001_fi_GFP.tif
  experience_XY002_phase.tif
  experience_XY002_fi_GFP.tif
  experience_XY003_phase.tif
  experience_XY003_fi_GFP.tif
```

Chaque TIFF contient la série temporelle sélectionnée. L’option d’extraction
d’un seul instant s’applique à toutes les positions. Si les canaux sont combinés,
un TIFF multicanal est créé par position. Les fichiers à une seule position
conservent leurs noms habituels, sans suffixe XY.

Les choix de plan Z ou de projection Z, de recadrage et de corrections
s’appliquent à chaque position indépendamment. Un même rectangle de recadrage
est appliqué à toutes les positions : vérifier qu’il convient à chacune.
L’aperçu reste limité à la première position ; le panneau d’information le précise.

## Premier essai sur les données du laboratoire

1. Utiliser une copie d’un petit ND2 contenant trois positions reconnaissables,
   avec deux canaux si possible, dans un dossier d’essai vide.
2. Ouvrir ce fichier dans **File Conversion**. Vérifier que le panneau
   d’information indique trois positions XY.
3. Garder **Save channels separately** activé. Pour le premier essai, désactiver
   les corrections et le recadrage afin de comparer directement les images.
4. Lancer la conversion. Vérifier les six TIFF dans **Tif_files**.
5. Ouvrir chaque TIFF dans BactoMate ou Fiji et comparer avec le fichier source :
   bonne position, bon canal, nombre d’instants et taille de pixel attendus.

Les tests automatisés utilisent un lecteur ND2 simulé et relisent les véritables
TIFF écrits. Ils couvrent plusieurs ordres de dimensions, des axes absents ou de
taille 1, les canaux séparés ou combinés, le choix d’un instant et d’un plan Z,
la projection Z, le recadrage et la calibration temporelle.

La conversion a également été validée sur un ND2 réel contenant trois positions,
trois canaux (GFP, mCherry, Phase nommé « PH3 ») et un seul instant : les neuf TIFF
de 1608 × 1608 pixels, en 16 bits, sont identiques pixel par pixel aux images du
ND2 et conservent la taille de pixel. Le canal Phase est reconnu même lorsqu’il
est le troisième canal du fichier. Un essai avec l’équipe reste recommandé pour
valider le parcours d’utilisation sur son ordinateur.
