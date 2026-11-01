# Segmentation contours and detached previews

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 1 November 2026.
[Manual](BACTOMATE_USER_MANUAL.md) · [Filtering curation](FILTERING_CURATION.md)

## Contours instead of opaque fills

Segmentation previews draw thin cell outlines over the original image, including
boundaries between touching labels. **Show cell outlines** controls visibility;
**Outline color…** changes colour immediately. The choice is remembered and used
for newly generated contour-overlay TIFFs. Cancelling the colour dialog preserves
the previous colour. Existing exported overlays are not rewritten.

Changing outline style does not rerun segmentation, relabel cells or change
quantitative measurements. Omnipose, Cellpose-SAM and U-Net share the contour
style where these previews are available. Use integer mask TIFFs for downstream
analysis, rather than RGB contour-overlay files.

## Detach and navigate

**Detach image** moves the same canvas to a movable window in the supported
Segmentation preview, including Omnipose and U-Net. The main controls compact at
the top to avoid the former blank image area. **Attach image** restores the layout.

The LUT histogram follows the image, stays open on its right and keeps separate
display ranges for channels/backgrounds during navigation. Move Min/Max lines or
use Auto. Viewing contrast does not change source intensity or segmentation.
Do not assume those view settings are saved across a full application restart.

Wheel zoom is gentle and centered at the pointer. Left-drag pans. Recenter/fit
restores the whole image; the two position sliders show/control the visible center.
Escape leaves the detached image open. Closing its cross offers Save / Discard /
Cancel. Save writes a rendered RGB TIFF/JPEG; cancelling the location keeps the
window open. Successful Save/Discard reattaches the canvas. This saves an image
view, not a new scientific mask or raw fluorescence stack.

The **24-segment default** elsewhere in Analysis is longitudinal profile sampling;
it does not change the neural segmentation diameter, model or flow thresholds.

## Check on your images

Compare outlines on isolated and touching cells and at image edges. Detach, zoom,
change contrast/channel, attach and confirm the view/settings stay coherent.
Test all close-dialog choices before a long session. Contours were reviewed on
three real XYs and interactions are tested with controlled data; native macOS
window behavior and biological segmentation quality still need local review.
