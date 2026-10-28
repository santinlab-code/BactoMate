# Affichage de la segmentation par contours

Les aperçus de segmentation affichent les cellules par des contours verts, avec
l’image Phase visible à l’intérieur des cellules. Les frontières entre deux
cellules qui se touchent sont également dessinées.

Dans la barre de l’aperçu :

- **Show cell outlines** permet de masquer ou réafficher les contours.
- **Outline color…** ouvre un sélecteur de couleur. Le changement est immédiat
  dans l’aperçu, sans relancer la segmentation. Annuler conserve la couleur.
- La couleur est mémorisée pour les prochains aperçus et exports de superposition.

Les TIFF de superposition nouvellement générés utilisent les contours. Changer
la couleur ne réécrit pas les TIFF déjà exportés. Les masques conservent leurs
identifiants de cellules pour les mesures et les étapes suivantes.

Les vues Omnipose, Cellpose-SAM et U-Net partagent ce mode d’affichage. Les
vignettes de l’aperçu de dossier utilisent aussi les contours lors de leur calcul.

## Fichier de référence de l’équipe

L’essai a été réalisé sur les trois positions du ND2 fourni, sur le canal Phase
nommé « PH3 », avec le modèle `bact_phase_omni`. Les canaux GFP et mCherry ont
été convertis avec les deux rôles **FI** et **Foci** : leurs noms contiennent
`_fi_foci_`. La détection de foci, la colocalisation et la fluorescence moyenne
seront évaluées séparément.

Les tests vérifient le choix et la mémorisation de couleur, l’annulation,
les frontières entre cellules, les bords d’image, la conservation du contraste
et des masques, ainsi que les exports sur plusieurs instants. Sur le fichier
réel, les superpositions des trois positions ont été relues et vérifiées.

## Image détachable

Les aperçus de segmentation Omnipose et U-Net proposent Detach image pour
déplacer l’image sur un autre écran. La même image, son zoom et ses données
restent actifs. La LUT suit l’image dans la fenêtre détachée ; les réglages de
segmentation restent dans le panneau principal.
Attach image ou fermer la fenêtre d’image réintègre le canevas. Masquer ou
fermer l’aperçu masque aussi sa fenêtre d’image.
