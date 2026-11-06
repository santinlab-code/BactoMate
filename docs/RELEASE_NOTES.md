# BactoMate Custom — release and development notes

Documentation updated **6 November 2026**, extending the November 1
code reference **`811d5b6`**.
Active custom branch: **BactoMate_Custom_New-Analyses**.
The package still reports upstream version 2.9.5; custom milestones below are Git
commits, not newly assigned upstream release numbers. These notes consolidate
the custom history; [the change summary](../MODIFICATIONS_BACTOMATE_EN.md) defines
current behavior and [the manual](BACTOMATE_USER_MANUAL.md) describes its use.

## 6 November 2026 — filter histories in settings pages

Cell and Foci histories and their details appear below the respective Cell filters
and Foci filters settings. Table pages keep the data rows; the two history views
remain synchronized, retain ten visible choices and continue to update after
filtering/curation and mask/frame changes. Small-viewport overflow and attached/
detached layouts remain available. The reference word “VDemo” is removed from
Demograph layout choices in the guide and advanced controls; calculations are
unchanged.

Validation: 15 targeted Linux tests passed (three existing pandas warnings),
including normal/enlarged fonts, repeated attach/detach, both filter histories
and their synchronization after object edits, plus Figure guide regressions.
Styled attached/detached pages were also inspected off-screen.

## 5 November 2026 — length-envelope demographs and curved-cell maps

Figure guide defaults to VDemo-style length-scaled columns, ordered by measured
centerline length, with fluorescence or local mask width (µm) as colour. The
earlier equal-length row layout and all 13 figure types remain available.

A new guide question maps mean fluorescence onto a reference capsule, with
black/white background and palette controls. A 64 × 32 grid interpolates only
within measured support; equal cell weighting and exported contributor counts
make aggregation explicit. Display sampling adds no optical resolution.

Automatic geometry follows curved centerlines through both caps, using local
normals and half-widths. Subpixel foci interpolate this nonlinear field instead
of a global affine fit, avoiding artificial lateral pole displacement while
preserving real off-axis positions. Existing ellipse metrics retain their
meaning; axial length/width, physical distances and geometry version are exported.
Ambiguous curved masks require curation. Rebuild older spatial figures from
masks/images to use the new coordinates. Point-density kernels are restricted
to the schematic capsule without relocating points. Figure options adds density
resolution/smoothing and background controls. Reproduction scripts preserve
background and draw the image before contour/point overlays.

Spatial/catalog worker results and completion use Qt receiver slots, so pending
signals disconnect when the Analysis receiver is destroyed. This addresses a
native crash encountered during consecutive GUI test windows.

Validation: **655 passed, 5 skipped** in the final Linux suite (18 warnings from
two existing warning types). New checks cover curved pole/lateral foci, rotation,
branched-mask rejection, length envelopes and missing bins, local width units,
equal-cell means, both backgrounds, Python reproduction, guided project loading,
missing raw-signal stripes and Excel sheet splitting. Real retained validation
masks: 114 cells processed, 76 using curved axes and 38 straight axes; fluorescence,
local-width and normalized-map figures/exports were inspected. This is a software
check, not biological localization validation. Native macOS/Windows and native
R/MATLAB execution remain to be checked locally.

## 5 November 2026 — consistent outlines and full-width Analysis

Single-image Segmentation uses Filtering's display resolution (up to 2048 px),
removing the former 1024 px reduction before one-pixel outlines were drawn.
Inference and scientific label masks are unchanged. Preview-start logging is also
compatible with Omnipose's formatter when multiple handlers consume a record.

Analysis settings occupy responsive groups across the full width; the old empty
figure area/sidebar split is removed. Simple mode uses two groups; advanced mode
keeps all controls in six groups with help icons. Conditions/replicates and Figure
guide remain at the top. **Show data table** is opt-in and opens all source rows
in a separate read-only window with lazy rendering; inspection does not change
plot settings. Figures remain independent windows. See [Analysis](NEW_ANALYSIS.md).

## 4 November 2026 — Filtering layout under constrained sizes

Separate Cell/Foci table and filter pages replace vertically stacked forms that
could be shrunk below their content height. Tables reserve ten rows after fonts
and headers are populated, with history below. Small-viewport overflow prevents
clipping; whole-control wrapping preserves checkboxes/actions. The attached image
sits beside the workspace; detachment releases its column and reattachment
restores it. Image selection opens the matching table, and View changes preserve
an open filter page. See [Filtering](FILTERING_CURATION.md).
Validation: **639 passed, 5 skipped** in the full Linux suite (two existing
warnings), including bounded styled previews with normal/enlarged fonts and
repeated attach/detach. Native platform visual verification remains pending.

## 4 November 2026 — reopen masks after resegmentation

Filtering automatically archives obsolete object curation and loads the new mask
when segmentation replaces a TIFF at the same path. Per-mask filter parameters
are retained; old IDs, geometry and history are kept in `curation_archive/`.
New label-pixel signatures preserve choices across metadata/storage-only rewrites,
with conservative migration for legacy records. Atomic JSON saves retry Windows
sharing locks and clean failed-write scratch. Old open editors cannot overwrite
new-segmentation curation. See [recovery behavior](FILTERING_CURATION.md#rerun-segmentation-into-the-same-folder).

## 3 November 2026 — shared Mac/Windows segmentation

A single native-resolution tiled inference path replaces differing preview/export
settings. Use GPU now applies to the single-image preview, with CPU available as
a reference on both platforms. A common pinned 16-package segmentation baseline
and CUDA version pins are verified by the installers, which rebuild environments
with backups and exercise actual CPU inference at diameters 30/33.

Shape-error recovery preserves input extent and diameter using recorded native-grid
resampling. Persistent failures abort rather than creating successful empty masks.
Destroyed preview controls disconnect their listeners. Preview caches fingerprint
pixels/weights/versions and clear disk entries. New environment/model/input/result
provenance is included in logs/sessions without extra per-image sidecars.

The retained real validation TIFF reproduces the one-pixel diameter-33 error and
recovers successfully on local CPU. Native Mac/MPS and Windows/CUDA equivalence
is not asserted. See [the comparison guide](MAC_WINDOWS_REPRODUCIBILITY.md).

## Current documentation revision

The English user manual, guides, setup/script/packaging instructions and current
PDF replace stale upstream/early-custom instructions. Testing and consolidated
changes also have French editions. Other former French topic guides are replaced
by English files and linked from the documentation index. Removed branches,
automatic PNG exports and obsolete control placements are no longer presented as
current instructions. Existing synthetic screenshots are explicitly illustrations.
This is a documentation update, not a new biological validation or application
version bump.

## 1 November 2026 — profiles, output and window refinements

Code: [`811d5b6`](https://github.com/santinlab-code/BactoMate/commit/811d5b6)

- Default 24-segment longitudinal profiles; optional native-pixel measurement plus
  interpolation onto 24 positions, with separate native export/provenance.
- Automatic pipeline PNG previews disabled; new bundles/scripts default PDF/SVG.
- Detached Segmentation controls compact; selected-cell colocalization title added.
- Figure windows brought forward safely; image/figure close crosses support
  Save/Discard/Cancel, with cancelled saving preserving the window.
- Export dimensions in cm/pixels, square default, and updated labels when the
  guide switches metric. Main-window deferred callbacks owned by its Qt lifetime.

Recorded validation: 614 passed / 5 skipped in the full suite, followed by 11
passing targeted checks after final refinements, including actual TIFF saving.

## 1 November 2026 — per-mask filtering and independent figures

Code: [`9a48cd6`](https://github.com/santinlab-code/BactoMate/commit/9a48cd6)

- LUT memory per mask/channel, including quick channel switching and dark settings.
- Exclude fully outside default, context menu and manual focus/polygon annotations.
- Shift-click selects only clicked objects; XY recipes/calibration independent,
  with inherited starting settings on first visit to a new mask.
- Batch mask/result selection restored; each export uses that mask's recipe.
- File audit reports identical content/table copies without deletion.
- Independent figure windows, off-screen export, per-window Figure options,
  category ordering/spacing, guided editing and verified-identity kymographs.

Recorded validation: 610 passed / 5 skipped, plus subsequent targeted checks.
These intermediate totals are historical, not the current suite count.

## 31 October 2026 — publication-style guided Analysis

Code: [`57c3078`](https://github.com/santinlab-code/BactoMate/commit/57c3078)

English four-step guide, Conditions & replicates available at the top in both
modes, automatic spatial source matching with filtered-mask preference, demograph,
normalized maxima and per-cell foci count layouts, explicit orientation and square
publication output. Brightest pixels and detected foci are separate sources.

## 31 October 2026 — session reset and automatic result loading

Code: [`b8127c4`](https://github.com/santinlab-code/BactoMate/commit/b8127c4)

Clear current session, directly visible right-side detached LUTs, Filtering XY
selector and automatic loading/opening of Analysis after final Analyze outputs.

## 31 October 2026 — simpler Analysis and explicit replicates

Code: [`cefd100`](https://github.com/santinlab-code/BactoMate/commit/cefd100)

Automatic result catalogue/cache, distinct data families, a simple measurement/
figure workflow, editable per-file conditions/replicates in analysis_groups.json,
replicate means and explicit frame selection. Advanced controls retained.

## 31 October 2026 — image navigation and retained contours

Codes: `5909d3e`, `9f14b5f`, `53ec722`

Per-channel LUT navigation, Escape-safe detached windows, right-side LUTs,
recenter/sliders, fixed Filtering panels, ten-row tables/history and focus-specific
clicking with kept/rejected markers. Thin configurable cell contours show only
retained cells; rejected cells remain recoverable through curation.

## 31 October 2026 — independent quantitative Analysis

Code: [`6cd5500`](https://github.com/santinlab-code/BactoMate/commit/6cd5500)

Initial standalone Analysis, advanced table-driven plots, image-derived spatial
profiles, explicit normalization/tracking requirements, exported source/plot data,
metadata and Python/R/MATLAB reconstruction. Later milestones extend the initial
11 plot types to the current 13 and replace its original PNG defaults.

## 28 October 2026 — initial custom pipeline and detached curation

Codes: `ff37fdf`, `f718acd`, `d874015`, `4715d8b`, `7e92cd7`

ND2 multiposition export/PH3 recognition, configurable segmentation contours,
manual cell/foci curation and persistent sidecars, calibrated cell tables/counts,
channel-specific filters and portable presets. Distance defaults 3 px / 2 px,
interactive foci distance view, multi-channel display, graphical LUTs, mouse
navigation and detached Segmentation/Filtering canvases. Curation actions/LUTs
follow the detached image. Later milestones supersede immediate right-click keep
and early control placement/PNG behavior.

## Branch lifecycle

Development began on test/bactomate-optimisations. It was renamed to
BactoMate_Custom_V1; a copy, BactoMate_Custom_Analyses, held initial Analysis work.
BactoMate_Custom_New-Analyses was copied from `53ec722` for the simpler interface.
At the user's request V1 and Analyses were subsequently deleted from GitHub.
Use only the active New-Analyses branch for this custom workflow. Historical
commits remain identifiers; deleted branch links are not installation targets.

## Baseline and earlier upstream history

The custom baseline is [`2dfd181`](https://github.com/santinlab-code/BactoMate/commit/2dfd181),
upstream BactoMate 2.9.5. It already includes the module shell, three segmentation
backends, FI/foci analysis, Tracking/lineage QC, Training, Post-processing and
platform setup/build helpers. For pre-custom upstream version history, read the
[baseline release notes](https://github.com/santinlab-code/BactoMate/blob/2dfd181/docs/RELEASE_NOTES.md)
or [upstream releases](https://github.com/Molinfect/BactoMate/releases).
Upstream binary downloads are not proof that the custom code is included.

## What has and has not been validated

Automated checks cover data selection, profiles/coordinates, curation/recipes,
windows/exports and executable Python reconstruction. Earlier real-image checks
covered nine pixel-identical TIFFs from a three-XY/three-channel/one-frame ND2,
contours on all XYs, and curation/export plus a 144-cell GFP demograph on XY001.
They do not establish biological foci/colocalization accuracy, all real time-lapse
formats, native macOS focus/close behavior or native R/MATLAB execution. Use the
[local test guide](../GUIDE_TEST_BACTOMATE_EN.md) and review scientific assumptions.

Validation on 3 November: **626 passed, 5 skipped** in the full Linux suite,
with two existing warnings; the actual CPU installer smoke test passed at both
diameters. Native macOS/Windows validation remains pending.

Validation on 4 November: **636 passed, 5 skipped** in the full Linux suite
(two existing warnings). Includes a real Qt Filtering reopen with a legacy
curation record, label/storage comparisons, archive preservation, stale editor
protection and simulated Windows locks/failures. Native Windows remains to test.

After the final button-width and image-selection refinements, five targeted
geometry/attach-detach checks passed again on the final code.

Validation on 5 November: **644 passed, 5 skipped**, two existing warnings in
the full Linux suite. Checks include responsive Analysis at three widths, all
source rows in the optional read-only window, table/session resets, unchanged
plot settings during inspection, and a 1608 px Qt Segmentation preview with
Filtering-identical outline pixels attached/detached. Model inference is stubbed
for this display regression; native Mac/Windows visual verification remains local.
