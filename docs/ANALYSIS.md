# Analysis methods, advanced controls and exports

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 5 November 2026.
[Simple workflow](NEW_ANALYSIS.md) · [Guided recipes](FIGURE_GUIDE.md)

## Scope and MicrobeJ reference

Analysis is an independent English-language module for existing measurements and
real image-derived profiles. Its property tables, sorted profiles and spatial/time
views are inspired by [MicrobeJ, Ducret et al. (2016)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5010025/).
**Advanced / MicrobeJ-style controls** is a BactoMate interface, not the Fiji plugin.
It does not claim MicrobeJ's subpixel contour model, pole-age identification,
clustering or all interactive tools. Methods/choices are recorded for comparison.

## Data and selection

The simple interface discovers project results automatically. Advanced **Load
tables (CSV / TSV / XLSX)…** accepts CSV/TSV and Excel XLSX/XLSM; each workbook
sheet is accessible. Compatible tables can be explicitly pooled with source_table
provenance. Catalogue data families keep Cells/Foci/Tracking/Profiles/Summary apart.
Known generated table copies are avoided by naming/role rules, not arbitrary
universal content deduplication.

Numeric fields can serve as metrics, text fields as groups. The advanced controls
select X, Y, Value, Group, sort column, exact-match filter and optional numeric
X bounds. Settings occupy responsive groups across the full page instead of a
narrow left sidebar. The values table is opt-in via **Show data table** and opens
in its own read-only window. All source rows can be inspected without copying or
editing the table; its table selector does not alter the plotting choices.
Computations use the entire selected dataset. Nonfinite values needed by a plot are removed. Redraw after
changing settings; each figure window holds a snapshot of rows/settings used.
Conditions/replicates assignments are saved separately in analysis_groups.json.

## The 13 figure types

| Figure | Inputs / aggregation |
| --- | --- |
| Histogram | X metric, optional groups; common bin edges across groups, counts |
| Scatter | Numeric X/Y, optional groups; selected observations |
| Mean curve | Numeric X/Y; mean and count per group/exact X value, no implicit SEM |
| Box plot | X measured metric; categories from Group; optional replicate means |
| Violin plot | X metric; Matplotlib KDE per group, constant groups shown as points |
| ECDF | X metric; sorted observations and cumulative fraction per group |
| Correlation | Numeric columns; pairwise Pearson with at least 3 paired observations |
| Demograph | Ordered length-scaled cell columns (guide default) or equal-length normalized rows; fluorescence or local width |
| Kymograph | Longitudinal position, time/frame, intensity; one verified identity/source |
| Normalized cell heatmap | Longitudinal/transverse positions and intensity; mean across occupied cell bins |
| Heatmap | Numeric X/Y and Value; mean per coordinate pair |
| Maxima map | Relative width/length; brightest-pixel or kept-focus points and relative density |
| Foci count | Nonnegative integer count per cell; percentages including zero counts |

For boxes/violins, the advanced **X / measured metric** becomes the vertical
measurement axis; Group supplies horizontal categories. The guide supplies friendly
axis labels. Correlation includes available numeric IDs unless they are removed
from the selected input table; do not interpret ID correlations as biological.
No plot automatically performs statistical testing or establishes biological
replication. Replicate points are means per condition/replicate over selected rows.

## Profile extraction

Advanced **Build profiles from mask + fluorescence…** selects matching label-mask
and single-channel fluorescence TIFFs for one XY. The guided path finds these
pairs in the project. They must have identical YX/TYX dimensions. Masks need
nonnegative integer labels; pixel calibration must be positive and finite.
Use filtered masks to restrict the population. Extraction runs off the GUI thread.

Outputs include Cells (one row per cell/frame) and Spatial profiles. The latter
contains separate longitudinal, 2D cell-map, brightest-pixel and available focus
rows. Figures select the appropriate profile subset. Coordinates include
position/transverse on −1…1, relative_position on 0…1 and relative_width on
−0.5…0.5. Raw intensity, contributing counts, source, frame, cell ID/object key
and calibrated cell metrics preserve provenance. Equivalent-ellipse length/width
in Cells are distinct from the centerline distance used for curved coordinates.

**Automatic — follow curved cells** is the extraction default. It tests a smoothed
pixel skeleton for curvature (arc/chord ratio above 1.015 and maximum deviation
above 0.75 px). Near-straight cells use PCA; curved cells use the medial axis.
Endpoints are extended through the measured caps. Projection onto continuous
centerline segments gives arc length and signed local-normal distance. Bilinear
mask sampling estimates each side's half-width; lateral coordinates divide by
that half-width and map into a fixed reference capsule (caps span one-sixth of
relative length). Raster overshoot is bounded at the local boundary. These are
pixel-derived methods, not MicrobeJ's subpixel contour model.

Explicit **Principal axis** and **Medial axis** remain available. PCA projects
onto a straight axis and cannot correct a curved cell. Branched/cyclic/disconnected
medial axes are rejected; automatic mode permits straight-axis fallback only for
near-convex masks (solidity ≥0.9). Inspect masks when geometry is ambiguous.
`axis_length_um` is centerline length; `local_width_um` is width across the local
normal. Existing `length_um`/`width_um` retain equivalent-ellipse semantics.
Exports record requested/actual methods and `geometry_version`.

**Geometric** orientation is deterministic from image coordinates and does not
identify pole age. **Bright pole** compares mean signals in terminal quarters and
reverses longitudinal/transverse direction when required to put the brighter end
at the negative/left/top side. It changes population alignment and is recorded.

### Longitudinal sampling

Default fixed sampling uses **24 segments** and means of actual contributing
pixels. Empty bins stay NaN; absent measurements are not set to zero. This default
does not alter neural cell segmentation settings or histogram bin counts.

Optional native sampling uses approximately one-pixel longitudinal bins, then
linearly interpolates their measured means onto 24 common positions. The first/
last measured means extend to edge positions. This makes rows comparable on a
common grid but adds no optical information. Rows distinguish `native measured`
from `native resampled`; resampled values have no fabricated pixel_count. The
bundle includes `native_profiles.csv` for that path. Advanced two-dimensional
maps retain measured bins (24 longitudinal × 16 transverse by default). The new
guided capsule heatmap instead uses a 64 × 32 display grid interpolated linearly
inside measured support, with no extrapolation. Source NaNs remain part of the
interpolation support; missing signal is not silently bridged by deleting them.
Rows record sampling mode and grid dimensions. Native longitudinal sampling does
not change how these 2D maps are sampled.

### Intensity normalization and missing values

Raw leaves fluorescence unchanged. Per-cell max divides the measured profile by
its maximum. Per-cell min–max subtracts its minimum then divides by its range.
Zero denominators map to zero; a constant profile is zero in min–max. Raw values
remain in a separate column on normalized exported source rows. These operations
do not perform background subtraction. LUTs are viewing contrast, not this
quantitative normalization. Check NaN in source/plot data before treating a white
strip as signal: empty bins are missing, while a bright colour can be near-white.

### Spatial aggregation and identities

The guide defaults to a VDemo-style demograph: one centered cell profile per
column, sorted stably by `axis_length_um`, preserving each cell's length relative
to the longest cell. Y is centered axial distance divided by half the longest
length; X is cell rank. Fluorescence defaults to raw units, with optional per-cell
normalization. Local mask width in µm is an alternative colour quantity and must
stay unnormalized. Display repeats each measured longitudinal bin over its extent;
missing bins remain missing. `cell_order.csv` records identities, order and lengths.
The earlier normalized-row layout remains available, including arbitrary sort
metrics. The programmatic FigureSpec default retains that legacy layout.

A 2D normalized cell heatmap averages per-cell positions equally; different
positions can have different contributor counts. The guide uses a straight
reference capsule and black background, editable to white. Advanced controls also
retain rectangular maps; the FigureSpec API retains its rectangular default.
`cell_coverage.csv` reports contributing-cell counts per position. Both maps are
distinct from a point-density maxima map. Missing regions show the selected
background and must not be interpreted as measured zero fluorescence.

Maxima map offers one raw brightest pixel per cell (first row-major pixel for ties)
or kept detections from saved Filtering foci data. Foci must belong to retained
masks. Subpixel focus coordinates use local bilinear interpolation of the
nonlinear per-pixel coordinates, replacing a global affine fit that displaced
pole foci on curved cells. Source x/y, axial µm and signed normal-distance µm are
retained. Relative coordinates use the same local-width capsule mapping as the
fluorescence map; this is a schematic reference, not a distance-preserving rigid
transform. Density defaults to a 96 × 96 histogram, Gaussian σ=2 bins, normalized
to peak 1 with values below 1% transparent. Its kernel is masked outside the
reference capsule without relocating points. Resolution, smoothing, points,
palette and black/white background are editable. Density is not fluorescence or
a probability density normalized to integral 1. No pole age is inferred.

Re-extract old spatial figures with the guide's automatic method to apply the
new geometry. Existing exported coordinates do not contain enough information
to repair curvature without the original masks and images.

Kymograph requires one source/XY, one verified track-ID group and at least two
time points. The guide can find Tracking masks, filters the chosen ID and
uses minutes with a known interval, otherwise frames. Ordinary labels require
explicit identity-continuity confirmation; there is no implicit tracking. Pole
orientation can still change during rotation and needs review.

## Advanced field recipes

| Figure | X | Y | Value | Other |
| --- | --- | --- | --- | --- |
| Demograph | relative_position | object_key | intensity / local_width_um | Sort axis_length_um; choose length-scaled columns or normalized rows |
| Normalized cell heatmap | relative_width | relative_position | intensity | Capsule or rectangle; filter intended population |
| Kymograph | position | frame/time | intensity | Group verified track ID; filter one ID and source; confirm continuity |
| Maxima map | relative_width | relative_position | — | Select maximum/focus source |
| Foci count | per-cell count column | — | — | Group condition; include zero-focus cells |

The guided path handles these mappings for the user. Advanced filters cannot
supply missing profiles, verified identities or biological replicate labels.

## Export bundle

Every figure window has its own rows, settings and export. **Export figure, data &
code…** creates a new timestamped folder containing the relevant files below.
The export works on an off-screen copy and does not resize the visible canvas.

| Artifact | Contents |
| --- | --- |
| figure.pdf / figure.svg | Default rendered figure; square 15.24 cm page unless changed |
| source_rows.csv | Rows actually used after selection/normalization |
| plot_data.csv | Aggregated values or plotted matrix, retaining missing positions |
| figure_data.xlsx | Source rows and Plot data, split into numbered sheets if needed; Replicates, Cell order and Cell coverage when applicable |
| cell_order.csv | Ordered object identities and measured lengths for length-envelope demographs |
| cell_coverage.csv | Contributing-cell count at each normalized fluorescence-map coordinate |
| replicate_summary.csv | Counts/means/SD for box/violin replicate groups when used |
| native_profiles.csv | Native longitudinal measurements when native sampling is used |
| figure.json | FigureSpec, labels, missing/normalization conventions and provenance |
| figure_geometry.csv / axes.json | Data-space primitives and axis/format settings for reproduction |
| palette.csv | Image-map colour lookup when applicable |
| manifest.json | SHA-256 hashes of bundle files |
| reproduce.py / reproduce.R / reproduce.m | Python, R and MATLAB reproduction scripts |

Automatic PNG output is off for pipeline previews and default figure bundles/
scripts. Explicit `formats=('png', 'pdf', 'svg')` at the export API or manual
figure save tools can still request PNG. Old files are not removed in bulk.

Figure options uses cm or pixels with DPI conversion, not user-facing inches.
Default size is 15.24 × 15.24 cm; at 300 DPI its raster equivalent is 1800 × 1800
pixels if explicitly saved as raster. PDF/SVG are vector formats, though heatmap
image layers remain raster elements. Screen/window size is independent of export.

## Reproduce outside BactoMate

Run `reproduce.py` from the bundle folder in an environment with NumPy, pandas
and Matplotlib, for example `python reproduce.py`. Open/run `reproduce.R` in
RStudio or `reproduce.m` in MATLAB with that directory as working directory.
Keep the geometry/axes/palette files beside the scripts and follow their headers.

Scripts redraw the stored computed primitives so KDE shapes, box statistics and
map colours need not be recomputed differently across languages. They do not
rerun segmentation, filters or the biological experiment. source_rows/plot_data
allow fresh analysis when desired. Renderer/font/export differences remain
possible; exact cross-language pixel identity is not claimed. Python execution
is tested; native R/MATLAB execution still requires validation in those tools.

The last recorded full code suite passed 614 tests (5 skipped), with 11 subsequent
targeted passes. Native macOS display and scientific interpretation require local
checks; use [the acceptance guide](../GUIDE_TEST_BACTOMATE_EN.md).
