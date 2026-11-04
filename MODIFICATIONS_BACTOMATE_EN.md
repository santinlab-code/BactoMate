# BactoMate Custom — consolidated changes

Updated: **4 November 2026**. The November 1 code reference was **`811d5b6`**;
section 13 describes the subsequent harmonization.
Baseline: upstream BactoMate **2.9.5**, commit **`2dfd181`** in this repository.
Active branch: **BactoMate_Custom_New-Analyses**.
[French edition](MODIFICATIONS_BACTOMATE_FR.md) · [Testing guide](GUIDE_TEST_BACTOMATE_EN.md)

This document describes the final cumulative behavior. It replaces the earlier
append-only notes, whose intermediate choices could contradict later fixes.
The former V1 and Analyses branches have been deleted from GitHub at the user's
request. Development and these docs use the active New-Analyses branch.

## 1. Multiposition conversion

ND2 conversion exports every XY independently, with separate channels or one
multichannel TIFF per XY. Names include `XY001`, `XY002`, etc. for multiposition
data. The selected time range remains in each stack. Channel roles, calibration,
Z selection/projection, cropping and correction options are preserved. Nikon
`PH3` phase recognition is corrected. The conversion preview shows the first XY,
so review the exported positions as well.

## 2. Segmentation and shared image controls

Cell previews use outlines rather than opaque cell fills. Outline colour is
selectable and remembered; changing it does not rerun detection or change labels.
New overlay TIFFs use the selected outline style; old files are not rewritten.

Segmentation and Filtering image canvases can be detached and attached. LUTs
follow the image, remain open on its right and retain separate channel contrast
settings during navigation. Filtering additionally keys LUT state by mask/XY.
This is viewing state, not a promise of contrast persistence after restarting.
Mouse-wheel zoom is gentle and pointer-centered; left-drag pans. Recenter/fit and
horizontal/vertical position sliders help navigation. Escape keeps the detached
window open, except that it can cancel an active manual polygon drawing.

Detaching compacts the main controls at the top; attaching restores their layout.
The close cross offers Save / Discard / Cancel. Saving a detached image writes a
rendered TIFF/JPEG, not a scientific mask or raw fluorescence file. Cancelling
saving keeps the window open. Closing successfully reattaches the canvas.

## 3. Filtering layout and calibrated tables

Cell/Foci tables and Cell/Foci filters now have independent fixed pages, with
room for ten table rows and history below them. Font/header-aware sizing and
small-viewport overflow prevent overlaps. The attached image is beside the pages;
detaching it returns the whole width to the workspace. Duplicate Import/Save
controls were removed from the left interface; **Import filter settings…** and
**Save filter settings…** appear when a filter page is selected.
The manual Keep/Exclude/Use filters actions follow the detached image with its LUTs.

The cell table reports area in µm², length/width in µm and X/Y centers in pixels.
Length and width are the major/minor axes of the equivalent ellipse, not skeleton
length. Calibration changes update physical dimensions. Invalid calibration does
not fabricate physical values. Counts and history refer to the current frame.
History records steps, parameters and before/after counts; it is not an undo stack.

## 4. Filtering selection, display and manual annotations

In a foci channel, clicking selects that channel's focus and its table row, rather
than its host cell. Cells mode selects cells. Table/image selection corresponds;
double-clicking a cell row centers the view. Shift-click adds only clicked objects,
without selecting intermediate table rows. Delete/Backspace excludes the current
selection reversibly. Applying filters keeps the current View channel.

Retained cells have thin contours, white by default, with a colour picker. Rejected
cells have no contour but remain available in the table. Detected or manually
annotated foci are green when kept and red when rejected/excluded. A yellow marker
indicates the current object selection; it does not override its biological status.

Right-click opens a menu rather than immediately adding an object:
**Add / keep object**, **Remove / exclude object**, **Create new object here…**.
A new focus is placed at the click in the current foci channel. In Cells mode,
click polygon vertices, then Enter/double-click to finish. Escape cancels the
polygon. It needs at least three pixels and cannot overlap an existing cell.
Manual objects are annotations, not new automatic detections. They enter tables
and filtered exports; manual foci are marked `manual` in the saved CSV.
Source images and original segmentation masks are not overwritten by these edits.

Keep overrides automatic rejection; Exclude overrides automatic acceptance;
Use filters removes the manual override. Decisions are scoped to frame, mask and,
for foci, channel. Curation and recipes are saved in the mask's `.curation.json`.
Changed source masks do not silently reuse old object decisions on new labels.

## 5. Independent XY/channel settings and batch filtering

**Mask / XY position** above the tables switches the active mask, image, foci,
curation and tables. Each visited mask retains its own cell filters, calibration
and per-channel foci filters. A new mask inherits the last settings as a starting
point; subsequent changes are independent. Channel switching saves/restores its
own thresholds and checkboxes without requiring Apply first.

New Filtering recipes enable **Exclude cells at borders** and **Exclude fully
outside** by default. Previously saved explicit values remain respected. These
Filtering defaults do not imply that all independent Analyze/CLI controls share
them; verify the selected stage's settings.

**Filter File/Folder** restores the selectable mask/result list even after preview
navigation to a single XY. Raw/filtered forms of one mask are grouped, with the
raw source preferred when available so exclusions can be reversed. Each selected
mask exports using its own saved recipe, without replacing the active XY's recipe.

Portable filter JSONs are separate from object curation: one cells file and one
file per named foci channel, also exported beside filtered masks. Importing a GFP
file leaves mCherry and cell settings intact. Legacy combined presets are accepted;
invalid/incompatible presets do not replace current settings.

## 6. Foci distance and colocalization preview

New defaults are **Max distance = 3 px** and **Threshold = 2 px**. Max distance
limits candidate partners; one-to-one assignment selects pairs, and Threshold
classifies matched pairs by center distance. Same cell only is respected. Help
icons explain both parameters. Existing sessions may retain other values.

The preview selects mask/XY, frame, cells and channels. Visible checkboxes permit
several background channels at once; the separate LUT-channel selector controls
which histogram is edited. Each image retains its LUT. Drag pans, wheel zooms
by about 5% per event and previous/next-cell buttons or arrow keys change cells.
Unused Home/Pan icons were removed. The selected cell title reads **Colocalized**
or **Not Colocalized** according to valid pairs involving that cell.

Foci centers are cyan/magenta; distance circles mark search/threshold radii;
green/orange links distinguish valid/above-threshold pairs. Pixel grid, 1 px
reference and available calibration aid interpretation. The preview uses the
analysis matching logic and updates its settings; it does not redetect foci or
write analysis results. Missing detection data is reported rather than invented.

## 7. Session and automatic Analysis handoff

**Clear current session** on the dashboard/File menu closes previews/figures,
clears paths, data caches and in-memory group assignments, then returns home.
Finish or cancel running work first. Disk files, saved project data and saved
`analysis_groups.json` are retained.

After successful **Analyze**, final measured/merged results are loaded and the
separate **Analysis** module opens automatically. Discovery supports multiple
output subdirectories and finding a neighboring `_analysis` folder from a mask
inside segmentation/filtered-mask folders. Refresh results rescans changes.
Unreadable files are reported. Known CSV/XLSX copies, figure bundles and redundant
aggregate workbooks are avoided by the catalogue rules; this is not universal
content-based deduplication of arbitrary renamed inputs.

## 8. A simpler English Analysis interface

The independent Analysis module is entirely in English. Simple controls select
population, figure, metric and frame. **Conditions & replicates…** stays at the
top in simple and advanced modes. A per-file table assigns conditions and biological
replicates, with batch edits saved in `analysis_groups.json`. Files/XYs from one
replicate may share a name. No biological replicate is guessed from an XY name.

Cell distributions and coloured replicate means are separate concepts; exports
include replicate counts/means/SD. First-frame defaults avoid implicitly pooling
a film. All frames is explicitly repeated observations. No implicit significance
tests or hierarchical model are added.

**Figure guide…** gives four steps: question, population, appearance, review/draw.
**Advanced / MicrobeJ-style controls** retains manual imports, axes, groups and
filters. It is a BactoMate interface inspired by MicrobeJ, not the Fiji plugin.
Cells, foci, tracking, profiles and summaries are kept as distinct populations.

## 9. Figure types and spatial measurements

There are **13 figure types**: Histogram, Scatter, Mean curve, Box plot, Violin
plot, ECDF, Correlation, Demograph, Kymograph, Normalized cell heatmap, Heatmap,
Maxima map and Foci count. All compatible numeric metrics remain accessible.

Spatial figures match project masks/channels automatically, preferring filtered
masks and reporting unfiltered inputs. Calibration comes from image metadata or
an explicit fallback. Principal-axis projection suits straight rods; medial-axis
pixel skeletons follow curved rods and reject ambiguous axes. Raw coordinates
and metrics remain exportable. Geometric orientation does not determine pole age;
explicit brighter-pole alignment places the brighter pole at left/top.

Demographs use one row per cell observation, sort by length and display relative
length 0–1. **24 longitudinal segments** are the default, not a change to neural
cell segmentation parameters. Optional **Native resolution → 24 positions**
measures at approximately one-pixel spacing, then linearly resamples onto the
common grid, holding the first/last measured means at the edges. Native values
are exported separately in `native_profiles.csv`. Interpolation adds no resolution.

Raw, per-cell maximum and per-cell min–max intensity choices are explicit. Direct
empty bins remain missing rather than zero; min–max maps constant profiles to 0.
A normalized maxima map distinguishes brightest raw pixel per cell from saved
kept foci; its relative point density and schematic capsule are not fluorescence
intensity or a measured average cell contour. Foci-count percentages use per-cell
counts including zeros, not a foci-only denominator.

Kymographs require one XY/channel, at least two frames and a verified cell/track
identity. The guide discovers tracked masks; ordinary segmentation labels require
explicit continuity verification. Time is minutes when an interval is known,
otherwise frames. No implicit tracking or biological pole assignment is performed.

## 10. Figure windows, styling and export

Every figure opens in its own movable window, raised in front of BactoMate, with
independent data/options/export. The live canvas fills the window. Export renders
an off-screen copy and does not resize or overlap the live figures. The default
page is square, **15.24 × 15.24 cm**. Export dimensions use **cm or pixels** with
DPI conversion. The normalized capsule uses an appropriate internal aspect ratio.

Figure options controls category order, labels/colours, box/violin X spacing and
width, axes/limits, X-label rotation, fonts, markers/opacity, lines, outliers,
legend/grid/title, colour scale and export dimensions/DPI. Edit with Figure guide
restores that window's recipe and options. Changing metrics clears stale axis
label overrides, so width no longer keeps the previous length label.

Escape keeps figures open. Closing an unsaved/changed figure offers Save / Discard /
Cancel; successful prior export allows closing directly. Cancelling export keeps
it open. Session reset/cleanup closes windows internally without individual prompts.

Default figure bundles contain PDF/SVG, CSV/XLSX source/plotted data, metadata,
SHA-256 manifest and reproduction scripts for Python, R and MATLAB. Optional
replicate/native-profile tables are included when relevant. Scripts redraw saved
geometry, not segmentation, and allow renderer/font differences. Python execution
is covered by tests; native R/MATLAB execution remains to be checked locally.

## 11. Output cleanup and inspection

Automatic pipeline PNG previews are disabled, including redundant filter preview
writes. New figure bundles and reproduction scripts default to PDF/SVG, without
PNG. Explicit manual PNG export remains available through figure save tools/API.
Existing PNGs are not removed in bulk; masks, TIFF visualizations and tables remain.

**File → Inspect generated files…** performs a read-only content/role audit,
reports identical files and CSV/XLSX table copies, and can save JSON. It deletes
nothing. Raw/filtered masks and aggregated/individual workbooks have distinct
roles. **Also save CSV** is off by default; enabling it intentionally duplicates
spreadsheet tables in an open text format.

## 12. Validation and practical limits

The latest full code test run recorded **614 passed, 5 skipped**, followed by
**11 passing targeted checks** after final window/activation refinements, including
real TIFF saving and colocalization-state updates. These are code checks, not
scientific validation of arbitrary microscopy data. This documentation rewrite
does not claim a new full application test run.

Earlier real-image checks covered a three-XY, three-channel, one-frame ND2: nine
16-bit TIFFs matched source pixels and calibration. Contours were reviewed for
all XYs; curation/export and a 144-cell GFP demograph were exercised on XY001.
Real ND2 time-lapse behavior, biological foci/colocalization accuracy, native macOS
window behavior and native R/MATLAB execution require local assessment.

See the [manual](docs/BACTOMATE_USER_MANUAL.md), [figure guide](docs/FIGURE_GUIDE.md)
and [test checklist](GUIDE_TEST_BACTOMATE_EN.md) for reproducible user workflows.

## 13. Mac/Windows harmonization — 3 November 2026

The core segmentation/reader versions are pinned identically on both platforms,
including DBSCAN 0.0.12. CUDA helpers preserve torch/vision/audio pins. Windows
now rebuilds its venv with a protected backup; both installers validate versions
and run actual CPU inference at diameters 30/33 before success.

Single-image/folder previews and saved Omnipose files use one native-resolution
tiled inference path. The preview's hardcoded GPU request is removed; Use GPU
is respected and visible in embedded controls. CPU is the comparison reference;
GPU kernels request stable cuDNN settings with benchmarking/TF32 disabled.
Fractional-diameter shape errors recover via recorded native-grid resampling,
without cropping or changing diameter. Unrecoverable read/inference errors stop
the run instead of saving an empty mask and reporting success. Preview control
connections are disconnected on destruction. Cache identities include pixels,
weights, package/engine versions; Clear Cache also clears disk entries.

Logs/session JSONs gain environment data and actual preview/inference fingerprints.
No extra per-image diagnostic sidecars/PNGs are added. New tiling alignment can
change historical export counts; this does not force the old 464-cell count.
The earlier real laboratory TIFF completed at diameters 30 and 33 on local CPU;
the latter reproduced and recovered the exact one-pixel error. Native Mac/Windows
verification remains required. See [the comparison guide](docs/MAC_WINDOWS_REPRODUCIBILITY.md).

The bundled phase/fluorescence checkpoint hashes are checked before built-in
loading. A mismatched file is reported without deleting it; restore the checkpoint
shipped with this branch or load different weights explicitly as a user model.

Validation on 3 November: **626 passed, 5 skipped** in the full Linux suite,
with two existing warnings; the actual CPU installer smoke test passed at both
diameters. Native macOS/Windows validation remains pending.

## 14. Segmentation to Filtering after rerun — 4 November 2026

Rerun segmentation over an already curated mask, then open Filtering. It must
load the new labels without “Cannot restore mask state”. The previous JSON is
preserved under `curation_archive/`; per-mask cell/foci filter parameters remain,
while old object overrides, manual geometry and history are not applied to new
labels. Rewriting identical label pixels with new TIFF metadata/storage must
preserve decisions for new-format records. Older records with a changed TIFF
are conservatively archived once. Mask TIFF contents must remain untouched by
this restoration. Expected `.curation.json` stores state; `.tmp` is temporary.
Windows sharing locks are retried and failed saves clean their scratch while
keeping the last valid JSON. Only owned scratch older than 24 hours is cleaned
on open. See [the curation guide](docs/FILTERING_CURATION.md).

Validation on 4 November: **636 passed, 5 skipped** in the full Linux suite
(two existing warnings). Includes a real Qt Filtering reopen with a legacy
curation record, label/storage comparisons, archive preservation, stale editor
protection and simulated Windows locks/failures. Native Windows remains to test.

## 15. Filtering layout without squeezed fields or overlapping histories

Cell/Foci tables and Cell/Foci filters use independent fixed pages. History stays
below each ten-row table; header/font-aware sizing also works after columns load
or the font changes. Whole controls wrap without disappearing during reparenting.
The attached image sits beside the pages in an adjustable divider; detaching it
returns the whole width to the workspace. Small viewports provide overflow while
preserving native field heights. Presets appear on filter pages. Image clicks open
the matching table; View changes preserve an open settings page.

Full Linux suite: **639 passed, 5 skipped**, with two existing warnings. Bounded
styled previews cover normal/enlarged fonts, both table types, fields, history,
manual controls and repeated attach/detach. Native Mac/Windows visual checks remain
part of local acceptance; the automated runs use offscreen Qt on Linux.

After the final button-width and image-selection refinements, five targeted
geometry/attach-detach checks passed again on the final code.
