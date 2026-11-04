# BactoMate Custom — user manual

**Branch:** BactoMate_Custom_New-Analyses

**Updated:** 4 November 2026; see the active branch for its current commit

**Upstream baseline/package version:** BactoMate 2.9.5 (`2dfd181`)

This manual describes the current custom application. The earlier V1 and Analyses
branches have been removed from GitHub. Upstream release binaries may differ.
For a local acceptance checklist use [the testing guide](../GUIDE_TEST_BACTOMATE_EN.md);
for the complete custom delta use [the change summary](../MODIFICATIONS_BACTOMATE_EN.md).

## 1. Install, launch and update

Use Python 3.11. Clone `santinlab-code/BactoMate` with
`--branch BactoMate_Custom_New-Analyses --single-branch`, or download/extract that
branch's ZIP. Run commands in the folder containing `main.py`.

macOS:

```bash
chmod +x setup/macos/*.sh launch_gui.sh
./setup/macos/install.sh
./launch_gui.sh
```

Windows, in a user-writable folder with 64-bit Python 3.11:

```bat
setup\windows\install.bat
launch_windows.bat
```

The installer creates the project's `venv`, installs dependencies and the editable
package, applies backend patches and performs a smoke check. CPU operation is
supported; accelerator availability depends on the backend/environment. Confirm
`python main.py --smoke-test` using that venv. A version string of 2.9.5 alone
does not distinguish custom revisions; use `git rev-parse HEAD` with Git.

For a clean Git checkout on the active branch, `git pull --ff-only` updates it.
Keep local edits before updating. ZIP users should extract a fresh source folder
and create its venv there. Do not move an old venv: launch scripts and editable
package paths can still point to the old installation. Never overwrite microscopy
results merely to update source. See [setup](../setup/README.md) and the
[Windows guide](INSTALL_AND_LAUNCH_windows.md).

## 2. Application map and session state

The dashboard and module navigation open File conversion, Segmentation, Tracking,
Analysis, Post-processing and Training. Segmentation contains the detection,
Filtering and Analyze stages. **Analyze computes measurements; Analysis draws
figures from them.** Session Logs and Help are available from the application.

Open a workspace folder to provide a project context. Saved project state uses
`bactomate_project.json`. Paths already selected in pipeline stages can also supply
an Analysis context. Status & Log reports progress and subprocess failures.
Save the relevant log when reporting a problem.

**Clear current session** on the dashboard or File menu closes previews/figures,
clears paths, Analysis tables/cache and in-memory assignments, and returns home.
Finish or cancel active processing first. It does not delete source images,
results, saved projects or saved `analysis_groups.json`. Reopening the same
project can therefore restore saved assignments; choose a new workspace for a
new experiment.

Session Logs can reload saved processing parameters without replacing current
input paths. They are separate from per-object curation, portable filter presets,
Analysis assignments and figure recipes.

## 3. File conversion and XY positions

Select ND2/LIF/CZI input using File conversion. Confirm metadata, calibration and
channel roles. Phase is the segmentation background; FI marks a fluorescence
measurement channel; Foci marks channels used for spot detection. A channel may
carry both fluorescence and foci roles. Names with `_fi_`/`_foci_` help subsequent
automatic matching; preserve the common sample and XY identity.

ND2 multiposition conversion processes every XY separately. With Save channels
separately, a three-XY/three-channel input gives nine TIFFs. Multiple positions
have `XY001`, `XY002`, etc.; single-position data keep conventional names.
The selected time series is retained in each stack. Combined-channel output
instead produces one multichannel TIFF per XY.

Time selection, Z plane/projection, crop and correction options apply to each XY.
A crop rectangle is reused across positions, so check all exported fields.
The preview shows the first XY. TIFFs normally go into `Tif_files` beside the
source unless an output path is chosen. Pixel/time metadata should be checked
before quantitative analysis. Nikon PH3 is recognized as phase. See
[ND2 details](ND2_MULTIPOINTS.md).

## 4. Cell segmentation

Choose the appropriate Omnipose, Cellpose-SAM or U-Net backend. Use phase/intensity
images, not an already rendered colour overlay. Select a built-in or compatible
trained model, check device and preview a small field before batch processing.

| Control | Interpretation |
| --- | --- |
| Model | Backend-specific pretrained or user-trained weights |
| Diameter | Estimated object size in pixels; auto behavior is backend-specific |
| Flow / mask thresholds | Model-output acceptance controls; tune against real boundaries |
| DBSCAN / clustering | Optional backend-specific mask reconstruction |
| Batch/device options | Throughput and memory use; CPU is available |
| Overlay/visualization | Saves visual QC images, separate from integer masks |

Process one file or a selected folder batch. Preview frame navigation and
re-detection help compare settings before a full run. Outputs commonly live in
`_segmentation*` directories with mask TIFFs and optional contour overlays.
Use the output paths reported in the log rather than inferring them from a screenshot.

Previews show cell outlines and preserve touching-cell boundaries. Show cell
outlines toggles them; Outline color changes colour without recomputing masks.
Newly exported contour TIFFs use that style. Equivalent-label masks, not these RGB
TIFFs, are the inputs to filtering, measurements and tracking.

### Shared Omnipose inference on Mac and Windows

Previews and saved-file/batch processing now share native-resolution tiled
inference with explicit normalization and parameters. Earlier exports used a
different tiling choice, so newly processed masks may differ from historical
exports. Use GPU is respected by the preview; uncheck it on both computers for
the CPU reference calculation. New installers verify the same pinned segmentation
libraries and run real CPU inference at diameters 30/33. MPS/CUDA numerical
equality is not guaranteed.

A one-pixel internal shape error is retried with native-grid resampling while
retaining diameter and image extent. An unrecoverable error aborts without
writing a new mask stack; it is not replaced with a successful empty mask.
New logs record actual device, parameters, input-pixel/checkpoint hashes and
versions. Bundled phase/fluorescence weights are validated before loading; a
different file under the same built-in name is reported without deletion.
Preview caches include these identities; Clear Cache clears disk
entries too. Controls disconnect when destroyed. See
[the Mac/Windows comparison guide](MAC_WINDOWS_REPRODUCIBILITY.md).

### Detached images and LUTs

Detach image moves the same interactive canvas into a movable window. The LUT
histogram follows it and is open on the right. Adjust its Min/Max lines or Auto;
changing channels preserves their individual display ranges during navigation.
Filtering keys these ranges by mask as well. This viewing memory is not an
on-disk LUT preset or a guarantee across application restarts.

Wheel zoom is pointer-centered; hold left-click and drag to pan. Recenter/fit
restores the overview, and horizontal/vertical position sliders move the visible
center. Escape keeps the detached window open. The parent controls compact at
the top while detached; Attach image restores their arrangement.

The close cross asks Save / Discard / Cancel. Save writes the rendered canvas as
RGB TIFF/JPEG; it is not a replacement for a label mask or raw intensity TIFF.
Cancelling a save keeps the window open. Successful Save/Discard reattaches the
canvas. During manual polygon creation, Escape cancels the polygon instead.
See [segmentation previews](SEGMENTATION_CONTOURS.md).

## 5. Filtering and manual curation

Open Filtering after detection. The image can remain detached while controls and
tables stay in the main interface. Cell filtering/Foci filtering are fixed panels;
cell/foci tables and histories provide space for ten rows. **Mask / XY position**
above them selects the active sample, mask, detections and curation.

### Cell filters and calibrated dimensions

Set pixel size in µm/px, area and length/width limits, aspect ratio, eccentricity,
solidity and optional out-of-focus rejection. Check calibration against metadata.
A zero/no-limit control should be read using its label/tooltip. New Filtering
recipes exclude border-touching cells by default; previously saved choices win.

Area is mask area × pixel-size². Length and width are calibrated major/minor axes
of the equivalent ellipse. They are not medial-axis lengths, even when later
profiles use a curved skeleton. The table shows these physical dimensions and
pixel X/Y centers; invalid calibration does not supply invented physical units.

Apply current filters preserves the View channel. Only retained cells have thin
contours, white by default, with a colour selector in the main and detached view.
Rejected cells stay in the table for possible reintegration.

### Foci channels and filters

Select a foci channel in View; clicking then targets foci in that channel rather
than their host cells. Depending on detection data, filters cover probability,
intensity/ratio, area and relation to cell boundaries. **Exclude fully outside**
is on for new recipes. It is distinct from other outside/touching options.

Kept foci are green and rejected/excluded foci red. Markers derive from saved
detections and explicit manual annotations, not arbitrary image maxima created
for display. Original detection CSVs keep rejected candidates available. A yellow
selection indicator is separate from kept/rejected status.

### Select and curate

| Input/action | Effect |
| --- | --- |
| Left-click object | Select its matching cell/focus table row |
| Shift-click | Add only clicked objects, without selecting intervening rows |
| Click background | Clear ordinary object selection |
| Double-click cell table row | Center image on the cell |
| Delete/Backspace with image/table focused | Exclude selected active-type objects |
| Keep selected objects | Force inclusion over automatic filtering |
| Exclude selected objects | Force exclusion over automatic filtering |
| Use filters for selected objects | Remove manual overrides |

These actions follow the image into its detached window. They are disabled during
processing. Exclusion is reversible; it does not erase the source segmentation.
Cell and foci decisions are independent, with frame/channel scope as appropriate.

Right-click opens Add / keep object, Remove / exclude object and Create new object
here. It never immediately changes kept status just by opening the menu. Existing
objects can be reintegrated or excluded. If the target is already in a multiple
selection, the relevant action can apply to that selection.

Create a focus at the clicked coordinate in its channel. In Cells mode, the first
click starts a polygon; add vertices and finish with Enter/double-click. Escape
cancels. The polygon needs at least three pixels and cannot overlap an existing
cell. Creations are manual annotations and appear in tables/filtered exports;
manual foci have a `manual` marker. Source images/masks remain intact.

### Recipes, curation and history

Each XY saves its cell filters, calibration and per-channel foci filters. Visiting
a new XY copies the last recipe as a starting point; revisiting an existing XY
restores its own values. Channel switching saves/restores values even before Apply.
LUT ranges remain independent from scientific filter thresholds.

The mask's `.curation.json` stores manual choices/geometry and local recipes.
Keep it with its source mask. A changed segmentation must not receive old object
choices against unrelated labels. After resegmentation into the same path, the
old record is preserved in `curation_archive/` and Filtering opens the new mask,
retaining filter parameters but resetting object choices/geometry/history. New
records compare label pixels, so TIFF metadata/storage-only rewrites preserve
choices. Legacy records with an already changed TIFF are archived conservatively.
The `.curation.json` is expected state; `.tmp` files are atomic-write scratch,
with Windows lock retries and cleanup. See [curation recovery](FILTERING_CURATION.md#rerun-segmentation-into-the-same-folder).
History records before/after counts, parameters and manual steps for the current
frame; it is a record, not an undo command.

Import/Save filter settings above the panels handles portable JSONs: one cells
file and one per named foci channel. Importing one channel leaves the others
unchanged. Old combined presets remain supported, with validation. Presets do not
transfer object-specific selections to unrelated images. See
[curation](FILTERING_CURATION.md) and [settings](FILTERING_PRESETS.md).

### Save a filtering batch

Filter File/Folder opens the available-mask list with result status, even after
previewing one XY. Select the masks to export. Raw and filtered variants of a
source are grouped; the raw source is preferred when present for reversible
curation. Each mask uses its own recipe. Outputs include filtered masks, foci
CSVs where relevant and portable filter settings. The active preview's recipe
is not substituted for all XYs. See [batch review](FILTERING_REVIEW.md).

## 6. Analyze: quantitative measurements

Select mask files/folder, normally using the saved filtered masks. Check the
Analyze-stage calibration and settings; independent Analyze/CLI controls do not
necessarily share every Filtering default. Include detailed per-cell data for
cell distributions, and enable FI/foci/colocalization outputs needed downstream.

Fluorescence measurement can use one selected FI stack or name-matched channels.
Review matching feedback and ensure XY/frame/shape agreement. Contour FI, when
enabled, measures an explicitly selected boundary band, not the whole cell.
Detection modes include manual/automatic rules and optional Spotiflow. These
methods have different candidate/blob definitions; do not treat a displayed peak
or manual annotation as evidence of biological localization without review.

When reusing saved segmentation/foci detections, choose the appropriate detection
CSV option rather than assuming a fresh independent detector produces identical
candidates. Per-channel processing and final merging complete before the
Analysis handoff.

Typical workbook roles:

| Table | One row represents | Typical content |
| --- | --- | --- |
| Summary | Frame | Counts, total/relative area and optional foci summaries |
| Per-Cell Data | Cell in one frame | ID, morphology, FI, foci counts/aggregates |
| Foci | Individual focus | Frame/channel, cell link, x/y, intensity and available blob metrics |
| Colocalization sheets | Matched focus pair | Partner identities, distance and valid/invalid status |

Available columns depend on chosen stages/channels. Join foci to cells using
source/XY, frame and cell identity; a cell number alone is not globally unique.
Combined/master workbooks summarize multiple files and should not be counted
again alongside their constituent rows. Also save CSV is off by default;
enabling it adds text copies of workbook data. Optional filter visualization is
TIFF; automatic PNG companions are disabled.

After successful Analyze and final merges, BactoMate loads the results and opens
Analysis automatically, including multi-folder outputs. No manual table import is
required for that workflow.

## 7. Foci distances and colocalization

Open Preview distances from foci analysis to inspect matching before interpretation.
Choose mask/XY, frame, two foci channels and cell. New defaults are Max distance
3 px and Threshold 2 px; saved sessions may differ.

Max distance defines candidate partner radius. A one-to-one assignment chooses
non-overlapping pairs. Threshold then counts a matched pair as colocalized when
its center distance is within the threshold. Same cell only restricts matches
when enabled. Raising Max distance alone does not make every pair colocalized.
The (?) controls explain the parameters and the preview shares Analyze's logic.

Cyan/magenta mark the channel centers; yellow/green circles show search/threshold
radii; green/orange lines indicate valid/above-threshold pairs. Above the selected
cell, Colocalized/Not Colocalized reflects valid pairs involving it. This is an
algorithmic distance classification, not proof of molecular interaction.

Checkboxes show phase and multiple fluorescence backgrounds. LUT channel selects
the histogram to edit; each channel keeps its contrast. Previous/next-cell buttons
and arrow keys navigate cells. Wheel zoom is gentle, and left-drag pans in both
views; the unused Home/Pan icons are gone. Calibration, a pixel grid and 1 px
reference assist distance reading. Preview edits update analysis settings, but do
not redetect foci or write analysis tables. See [distance preview](FOCI_DISTANCE_PREVIEW.md).

## 8. Tracking and identity

Tracking uses Trackastra on a mask time series. Select the masks and optionally
the corresponding original TIFF and analysis workbook. Models include general_2d
and general_2d_w_SAM2_features. Modes include greedy, greedy_nodiv and ILP; the
latter needs compatible solver dependencies from requirements. CPU/CUDA/MPS
availability depends on the environment.

Review lineage QC, uncertain links and divisions before exporting tracked masks
and lineage data. Persistent CellIDs can be assigned/preserved in supported
workflows, but a segmentation label is not automatically a persistent track.
The CLI assign_persistent_ids tool can help build IDs; it does not replace
visual continuity/division verification. Kymographs use one verified identity
and can discover tracked mask exports in `_tracking`.

## 9. Analysis: results to figures

The separate Analysis module is entirely in English. On entry/Refresh results it
uses the workspace or pipeline context to discover result CSV/TSV/XLSX/XLSM.
Completed Analyze results are supplied directly after the run. The catalogue
caches unchanged files and reports unreadable ones. Known figure exports,
CSV/workbook copies and redundant aggregate workbooks are avoided by naming/role
rules, not by a universal arbitrary-file deduplication algorithm.

Cells, Foci, Tracking, Profiles and Summary are separate families. Do not use a
summary table to represent individual cells. Manual imports remain in Advanced
mode for external data. See [simple Analysis](NEW_ANALYSIS.md).

### Conditions and replicates

Conditions & replicates stays at the top in simple/advanced modes. Assign each
source file a condition and biological replicate, optionally editing selected
rows together. Several XYs from one replicate should share a replicate name.
Choices are saved in `analysis_groups.json` at the catalogue root. Nonempty
assignments override source columns; blank assignments keep source information.
The application does not infer biological replication from files or XY numbers.

For an area violin: Cells → Violin plot → Cell area (µm²); choose a frame, Compare
conditions and Show replicate means. Each violin represents cell observations;
coloured points are replicate means within condition. First-frame defaults avoid
unintentional film pooling. All frames explicitly includes repeated observations.
No statistical test or hierarchical model is implicitly added.

### Figure guide and advanced controls

Figure guide follows four steps: question, population, appearance, review/draw.
It finds project masks/channels for spatial figures, prefers filtered masks and
reports unfiltered inputs. Spatial computation runs in the background. Advanced /
MicrobeJ-style controls keeps manual tables, free axes/groups/filters and profiles.
This is inspired by MicrobeJ, not an integration of the Fiji plugin.

All 13 types are available: Histogram, Scatter, Mean curve, Box plot, Violin plot,
ECDF, Correlation, Demograph, Kymograph, Normalized cell heatmap, Heatmap, Maxima
map and Foci count. The [methods reference](ANALYSIS.md) defines their aggregation
and required fields. The [figure guide](FIGURE_GUIDE.md) provides recipes.

### Spatial profiles and intensity

A demograph has one row per cell observation, sorted by length, with relative
longitudinal position 0–1. Principal axis is a straight projection; medial axis
uses a pixel skeleton for curved rods and rejects ambiguous/branched axes.
Cell-table length/width still use the equivalent ellipse. Geometric alignment
does not infer pole age; optional brighter-pole alignment places it at left/top.

Default longitudinal sampling is 24 segments. Native resolution → 24 positions
measures about one pixel apart then interpolates onto a common grid; edge values
hold the first/last measured mean. `native_profiles.csv` preserves native samples.
Neither interpolation nor more segments adds optical resolution. Direct empty
bins stay missing; they must not be interpreted as zero fluorescence.

| Intensity choice | Formula per cell profile | Main use |
| --- | --- | --- |
| Keep absolute fluorescence | I | Compare measured brightness with comparable acquisition/calibration |
| Scale each cell to its maximum | I / max(I) | Compare distribution shapes while retaining relative baseline |
| Scale each cell from 0 to 1 | (I − min(I)) / (max(I) − min(I)) | Compare contrast patterns after removing each profile's minimum |

Raw values remain available. A zero denominator maps the normalized profile to
zero. These intensity choices do not replace background correction. LUT contrast
is independent of this quantitative normalization.

Maxima map distinguishes brightest raw pixel per cell from kept detected foci.
Its capsule is schematic and its density is relative point density; neither is a
measured cell shape or fluorescence heatmap. Foci count uses per-cell counts,
including zeros. Kymographs require one XY/channel and verified identity in at
least two frames; time uses minutes when known, otherwise frames.

## 10. Figure windows, options and export

Each draw creates an independent movable figure window, raised in front of
BactoMate with its own data and settings. Show latest figure reopens the latest
view. Resizing/exporting a figure does not overwrite another. The live canvas
fills its window; export uses a separate off-screen copy.

Figure options includes title/axis labels and limits; category order, display
labels and colours; box/violin spacing and width; fonts, X-label rotation,
points/opacity, lines/outliers, legend/grid/title; image colour bounds; export
size in cm or pixels and raster DPI. Default size is square, 15.24 × 15.24 cm.
A normalized-cell schematic has its own appropriate plotting aspect inside that
page. Numeric X distances are data; category-spacing controls chiefly apply to
boxes/violins. Edit with Figure guide restores that figure's scientific recipe
and publication options. Changing the metric clears old axis label overrides.

Escape keeps the window open. The close cross asks Save / Discard / Cancel for
an unsaved or changed figure. Save exports the figure/data/code bundle; cancelling
its folder selection keeps the figure open. An unchanged successfully exported
figure can close directly. Internal session reset closes figures without an
individual save prompt: export wanted figures before resetting.

Exports create a new timestamped figure folder containing PDF/SVG, source and plot
CSV tables, an Excel workbook, figure settings/provenance, SHA-256 manifest and
Python/R/MATLAB scripts. Replicate summaries and native samples appear when used.
Automatic PNGs are disabled; an explicitly requested manual PNG is still possible.
Scripts redraw saved geometry, not original segmentation; Python execution is
tested, while native R/MATLAB execution and renderer/font equivalence need local
checks. See [methods and exports](ANALYSIS.md).

## 11. Training and post-processing

Training provides a shared dataset workflow plus backend-specific Omnipose,
Cellpose-SAM and U-Net controls. Use matching raw image/integer-mask pairs and
hold out validation images. Configure tiling, epochs, learning rate and output
according to the backend. A compatible user-trained model must still be tested
on images outside its training set. Check pipeline and model-inspection tools
help diagnose incompatible checkpoint metadata, flat outputs or loading failures.
If a custom Omnipose model finds no cells, verify loader patches and thresholds;
a more permissive mask threshold can help diagnose it but does not repair poor
weights or guarantee a useful model.

Post-processing provides scale bars, montages and growth-curve videos. Scale bars
require correct µm/px, length, position, colour and label settings. Montage groups
matching channels, normally phase → fluorescence → merge, and uses the first
frame; control grid, spacing, labels, colours and LUTs. It is a display product,
not a replacement for raw channels.

Growth-curve video combines a TIFF series with Summary data such as Frame and
Total Cell Area (Relative). Set minutes per frame, graph limits, playback FPS and
TIFF/AVI/GIF/MP4 outputs. Playback speed is distinct from biological time. Relative
area is referenced to the first frame and is not an independent cell count.

## 12. Files, audits and troubleshooting

| Artifact | Keep it for |
| --- | --- |
| Raw/converted channel TIFF | Source pixels, metadata and matching |
| Integer segmentation mask | Original detected objects and reversible curation |
| `.curation.json` | Decisions, manual geometry and local mask/channel recipes |
| Filtered mask/foci CSV | Selected population used for downstream measurements |
| `.filter_settings.*.json` | Portable cell or named-channel filters |
| Analysis workbook/optional CSV | Quantitative rows and summaries |
| `analysis_groups.json` | Saved condition/replicate assignments |
| Figure bundle | Figure-specific rows, geometry, settings and reproduction code |

File → Inspect generated files is read-only. It compares identical content and
known table copies, reports roles and can save JSON; it never deletes files.
Raw vs filtered masks and individual vs combined workbooks can be intentional.
Automatic pipeline PNG previews are disabled; existing PNGs are not bulk-removed.
Documentation PNG illustrations are separate from results.

If Analysis finds nothing, check the current workspace/pipeline context, wait for
Analyze to finish and use Refresh results; review read errors. For a missing
spatial channel, check common sample/XY names, shapes, calibration and filtered
outputs. For an empty demograph, inspect masks, finite intensity and the chosen
population. For white/missing strips, inspect NaN bins in plot_data.csv before
changing sampling; bright colormap colours can also be near-white.

For Qt startup problems on macOS use setup/macos/repair_pyqt6.sh or recreate the
venv. On Windows check Python 3.11 x64, VC++ runtime and the dependency repair
commands in the Windows guide. Use the launcher/venv rather than another Python.
For model/backend failures run Check environment/Check pipeline and preserve the
log. Reduce batch size/use CPU when GPU memory is insufficient.

## 13. Evidence and limits

The earlier November 1 suite passed 614 tests with 5 skipped, followed by targeted
checks. The November 3 harmonization adds dedicated regression and real-image
CPU checks; see the comparison guide and release notes for current evidence. Real checks covered a single-time,
three-XY/three-channel ND2 with pixel-identical converted TIFFs, contour review,
XY001 curation/export and a 144-cell GFP demograph. Synthetic tests cover further
interactions. These results do not certify biological foci detection/colocalization,
all real time-lapses, native macOS window behavior or native R/MATLAB execution.
The documentation update itself is not a new full application test run.

## References

- [BactoMate upstream and citation](https://github.com/Molinfect/BactoMate)
- [MicrobeJ methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC5010025/)
- [Omnipose](https://omnipose.readthedocs.io/)
- [Cellpose](https://cellpose.readthedocs.io/)
- [Trackastra](https://github.com/weigertlab/trackastra)
- [Documentation index](README.md), [CLI reference](../bactomate/scripts/README.md)
- [Release notes](RELEASE_NOTES.md), [paper data](PAPER_DATA.md)
