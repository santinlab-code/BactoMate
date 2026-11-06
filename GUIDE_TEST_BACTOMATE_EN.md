# BactoMate Custom — installation and acceptance tests

Updated: **6 November 2026**, branch
**BactoMate_Custom_New-Analyses**. [French edition](GUIDE_TEST_BACTOMATE_FR.md)
· [Consolidated changes](MODIFICATIONS_BACTOMATE_EN.md)

Use a copy of a small dataset in a separate test folder. A useful dataset has
several XYs, phase, GFP and mCherry; add a tracked time-lapse for kymographs.
Record commit, OS, calibration, input files and expected channel names. These
checks validate behavior; biological detection accuracy needs separate review.

## 1. Install the correct branch

[Clone or download the active branch](README.md#install-this-custom-version).
Upstream release apps do not guarantee these customizations. The former V1 and
Analyses branches have been removed. Use Python 3.11 and create a venv at the
final project path. Recreate it rather than copying an old folder's venv.

macOS, Terminal in the folder containing `main.py`:

```bash
chmod +x setup/macos/*.sh launch_gui.sh
./setup/macos/install.sh
source venv/bin/activate
python main.py --version
python main.py --smoke-test
./launch_gui.sh
```

Windows, Command Prompt in the project folder:

```bat
setup\windows\install.bat
venv\Scripts\python.exe main.py --version
venv\Scripts\python.exe main.py --smoke-test
launch_windows.bat
```

The package version can remain **2.9.5**. With Git, `git rev-parse HEAD` identifies
the custom revision. See [setup](setup/README.md) for repairs and updates.

## 2. Home and session reset

Open a project/workspace folder. Confirm Analysis is a separate navigation module.
Set a few paths, then use **Clear current session** on the home page. Expect empty
paths/caches, closed previews/figures and a return home. Saved files and saved
condition/replicate assignments must remain on disk. Reset must not interrupt
active work silently; finish/cancel it first.

## 3. Convert a multiposition ND2

Select the ND2 in File conversion. Check reported positions/channels and channel
roles. For the first comparison, disable crop/corrections and save channels
separately. Run conversion; for three XYs × three channels expect nine TIFFs in
`Tif_files`. Check XY/channel identity, frame count, bit depth and pixel size in
BactoMate or Fiji. Preview is the first XY, not a composite of all positions.
A single-time reference dataset cannot validate time-lapse export.

## 4. Segment and detach the image

Select phase and an appropriate backend/model. Preview segmentation, inspect
boundaries, hide/show outlines and change colour. Source labels must not change
when only the display colour changes. Save/process a small test before a batch.

Detach the image. Expect compact controls at the top of the main interface, LUTs
open on the right of the detached image, gentle wheel zoom, left-drag pan,
recenter/fit and both position sliders. Adjust each available channel's LUT,
switch away/back and confirm the separate ranges remain. Escape keeps the image
open. Attach restores the layout and values.

Test the close cross: Cancel leaves it open; Save opens a TIFF/JPEG dialog;
cancelling that dialog leaves it open; successful Save or Discard reattaches it.
The saved view is rendered RGB, not a new scientific label mask.

## 5. Filter cells and foci on each XY

Open Filtering and choose **Mask / XY position**. Inspect **Cell table**,
**Foci table**, **Cell filters** and **Foci filters**. Expect ten table rows with
history below the settings on the respective filter pages, intact fields and no
large empty detached-image area. Import/Save
presets appear on the filter pages. Try normal/larger fonts, resize the pane,
attach/detach twice and drag the image/pages divider. No controls or rows may
overlap; overflow must remain accessible if the viewport is too small.
New recipes have border-cell exclusion and **Exclude fully outside** enabled.
Previously saved choices can override defaults.

Confirm area is µm², length/width µm and X/Y pixels. Change calibration on a test
XY: physical dimensions should update; the source mask should remain unchanged.
Length/width are equivalent-ellipse axes. Apply filters while viewing GFP: View
must stay on GFP. Switch GFP↔mCherry quickly after changing each LUT; neither
contrast range should reset.

| Action | Expected result |
| --- | --- |
| Left-click cell in Cells mode | Matching cell row selected |
| Left-click focus in its foci channel | Focus row selected, not its host cell |
| Shift-click two distant objects | Only clicked objects selected |
| Double-click cell row | Image centers on that cell |
| Delete/Backspace | Selected objects excluded reversibly |
| Keep selected objects | Manual inclusion overrides the filters |
| Use filters for selected objects | Manual decision removed |
| Right-click | Menu opens; no immediate inclusion |

Only retained cells have thin contours. Choose their colour. Kept foci are green,
rejected/excluded foci red; markers must refer to detections/manual annotations.
Exclude a focus and confirm its cell is still retained. Reject all cells and
confirm no residual cell contours remain.

Create a test focus at an empty clicked location in a foci channel. In Cells
mode, create a polygon, finish with Enter/double-click, then try Escape to cancel
a second polygon. Confirm manual objects reach tables/filtered exports, manual
foci carry `manual`, and original image/mask files are unchanged.

## 6. Independent settings, persistence and batch export

On XY1 choose distinct cell/GFP/mCherry filters and calibration. Visit a new XY2:
it inherits these as a starting recipe. Change XY2; return to XY1 and confirm its
original recipe. Reopen the preview and check saved curation/recipes. Confirm
GFP and mCherry thresholds remain independent even without Apply before switching.

Save cells and channel presets. Import GFP alone; mCherry/cells must not change.
Object-specific choices are in `.curation.json`, not transferable presets.

After visiting individual XYs, run **Filter File/Folder**. Expect the full mask
selection list with result status. Export multiple XYs; compare their distinct
recipes, filtered masks/foci and portable settings files. Raw/filtered versions
should represent one source entry when paired. History counts concern the frame
being viewed, and selecting history is not an undo operation.

## 7. Foci distance preview

With two detected channels, open **Preview distances…**. Check defaults 3 px
Max distance / 2 px Threshold on a fresh session; use (?) help. Choose XY, frame
and cell. Previous/next buttons and arrow keys must change the selected cell.
Check multiple background channels, edit each histogram LUT and confirm others
are preserved. Drag to pan; wheel zoom should be gentle in both views.

Inspect cyan/magenta centers, yellow search radius, green threshold radius and
green/orange pair links. The cell title must update **Colocalized / Not
Colocalized** with valid pairs and threshold changes. No detected CSV means an
information message, not artificial foci. Previewing must not write result tables.

## 8. Run Analyze and verify automatic loading

Finish Analyze with the desired FI/foci/colocalization choices. Wait for final
measurements and channel merging. BactoMate should load the results then open
**Analysis** automatically, for one file or several output subdirectories.
Cells, foci, profiles/tracking and summaries must remain distinct data families.
Refresh results should pick up modifications and report unreadable files.
Known workbook/CSV and aggregate copies should not double the observation count.

## 9. Conditions, replicates and a violin plot

In **Conditions & replicates…**, assign X/Y and R1/R2/R3 per source file. Give
multiple XYs from the same biological replicate the same replicate name. Save,
reopen and verify persistence in `analysis_groups.json`. In simple mode select
Cells → Violin plot → Cell area (µm²), Compare conditions, Show replicate means
and a frame. Expect cell distributions and one coloured mean per replicate and
condition, not one replicate per XY. Check the exported Replicates sheet/CSV.

## 10. Figure guide, spatial plots and kymographs

Follow Question → Population → Appearance → Review/draw. Draw a demograph for
one channel/condition/frame. Check the length-scaled column envelope and the
alternative normalized-row layout with 0–1 relative length. Default sampling is
24 longitudinal segments. Compare raw,
per-cell max and min–max intensity; direct missing bins must not masquerade as
zero fluorescence. Native sampling should also export `native_profiles.csv`.

Draw a maxima map first with brightest pixel, then with kept detected foci.
Confirm the source distinction and normalized axes; density is relative point
density, not fluorescence. Draw Foci count from a per-cell count column and verify
cells with zero foci are included.

For a time-lapse, choose one XY/channel, a tracked mask and one verified ID.
Confirm continuity, choose a time interval if available and draw a kymograph.
Expect at least two time points, longitudinal axis 0–1, and minutes or frames on
the temporal axis. Unrelated cell labels must not be silently linked.

## 11. Figure windows, options, exports and closing

Generate several figures: each should appear in front in its own movable window.
Resize/export one; other windows and their figures should stay independent. The
live canvas fills its window; the default exported page is square.

Use Figure options: change category order/labels/colour, box/violin spacing/width,
limits, fonts, legend/grid, colour bounds and cm/pixel export size. Verify an
exported page's dimensions. Edit a length figure with Figure guide, choose width
and redraw: Y label must change to width. Re-edit an older window to ensure its
own choices, not the latest other figure, are restored.

Export figure/data/code. Expect PDF/SVG, CSV/XLSX, metadata/manifest and scripts;
no automatic PNG. Test Cancel, Discard and Save on a new unsaved figure's close
cross. Cancelling folder selection keeps it open. A figure already exported and
unchanged can close without asking again. Escape keeps it visible.

## 12. Output audit and reproducibility

Run **File → Inspect generated files…**. Review raw vs filtered roles, identical
files and CSV/XLSX copies; optionally save the report. It must not delete files.
New pipeline runs must not add PNG previews; existing PNGs are not bulk-deleted.
Manually requesting a PNG is still possible with figure save tools.

Run the bundle's `reproduce.py` from its directory with Python, NumPy, pandas and
Matplotlib installed. Open the R/MATLAB scripts in those tools if used locally.
Compare geometry, labels and colours, allowing font/renderer differences. The
scripts redraw saved primitives; they do not repeat segmentation or reanalysis.

## Test record

Record pass/fail, input/XY/frame/channel, steps, expected/observed result and log
path. Preserve sources, curation, filter presets and a failing figure bundle.
The 5 November Linux suite recorded **644 passed / 5 skipped** (two existing
warnings), including replaced-mask recovery, simulated Windows locks and bounded-layout
checks with enlarged fonts and repeated attach/detach, plus full-width Analysis,
its optional read-only table and matching Segmentation/Filtering outline pixels.
The actual CPU installer inference passed at diameters 30 and 33 on 3 November.
These checks do not replace native Mac/Windows testing or biological review.

## 13. Mac/Windows reference comparison — 3 November 2026

Update source and rerun the platform installer so the shared dependency versions
are applied. Preserve/archive an existing venv.previous before another reinstall.
Confirm baseline and real CPU segmentation checks pass. Use the same phase TIFF,
model and parameters, uncheck Use GPU on both machines and Re-detect before
comparing preview/export. Check pixel/weight hashes, effective device, versions,
parameters and recovery mode in the new logs, not only the displayed model name.

Test diameter 33: any shape recovery must preserve dimensions/diameter and be
recorded. An unrecoverable error must fail the run without writing a new empty
mask stack or reporting success. Close/reopen the preview and change controls;
no deleted-QDoubleSpinBox error should occur. Clear Cache must invalidate disk
previews. Expect historical file-export counts to change when old non-tiled
exports are replaced by the common tiled computation. See
[the full comparison procedure](docs/MAC_WINDOWS_REPRODUCIBILITY.md).

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

## 16. Matching contours and full-width Analysis — 5 November 2026

Compare a 1608 px mask in single-image Segmentation and Filtering at matching
zoom/colour: the same one-pixel edges should be visible, including small objects.
Segmentation no longer draws these edges on a 1024 px display reduction; detection
and scientific masks stay unchanged. Repeat attached and detached.

Analysis keeps Conditions & replicates and Figure guide at the top. Advanced
settings use six full-width responsive groups, with one to three columns; simple
choices/actions use two groups. No embedded values table or empty figure area is
shown. **Show data table** opens a read-only window with all source rows. Check
rows beyond 100, change its inspected table without changing plotting choices,
close/uncheck/reopen it, and reset the session. Figure windows, guide editing,
exports and automatic result loading must remain functional.


## 17. VDemo envelopes and curved-cell maps — 5 November 2026

From Figure guide choose demograph, channel and retained population. Keep
Automatic cell shape and length-scaled columns: short cells must precede long
cells, centered at zero, with an increasing length envelope. Y is axial distance
divided by half the longest length. Compare fluorescence with Local cell width
(µm); width stays in physical units even after a previous intensity normalization.
Test normalized rows and native sampling. Check `cell_order.csv` against matrix
columns. Missing measured bins must remain missing.

Choose Map fluorescence on a normalized cell. Compare black/white backgrounds,
palettes, raw/per-cell scaling and separately selected conditions. Expect a capsule
mean with equal contributing-cell weights and no extrapolation beyond measured
support. Check `cell_coverage.csv`, CSV/XLSX, background and contour layers after
Python reproduction. Large tables must split into numbered Excel sheets without
lost rows; CSV remains complete.

Use a curved vibrioid mask with known pole foci, an axial body focus and a real
lateral focus. Compare Principal axis with Automatic: pole/axial points should
remain near the local axis while the lateral focus stays offset. Check raw x/y
and physical normal distance in exports. Rotate input by 90°: absolute lateral
offset and distance to the nearer pole should agree within pixel-method precision.
Branched curved masks must report an error instead of invented coordinates.
Check density smoothing/resolution, points and backgrounds. Rebuild older spatial
figures from masks/images to apply corrected coordinates. Repeat drawing/editing/
closing figures and changing projects during extraction: stale results must not
affect another project or a destroyed Analysis receiver.

Final automated Linux suite: **655 passed, 5 skipped**, 18 warnings from two
existing warning types. Spatial checks include synthetic ground-truth pole/
lateral positions and real 114-cell mask extraction with inspected figures and
exports. Native Mac/Windows and R/MATLAB execution remain local acceptance tests;
software checks do not validate biological pole identity or localization accuracy.
