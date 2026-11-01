# Analysis methods, advanced controls and exports

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 1 November 2026.
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
X bounds. A preview shows up to the first 100 rows; computations use the entire
selected dataset. Nonfinite values needed by a plot are removed. Redraw after
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
| Demograph | Longitudinal position, object key, intensity; rows sorted by a cell metric |
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

**Principal axis** projects mask pixels onto a straight PCA axis; it does not
straighten curved cells. **Medial axis** uses a pixel skeleton and nearest-centerline
projection with cumulative distance, rejecting branched/cyclic/too-short ambiguous
axes. These are pixel methods, not MicrobeJ subpixel contours.

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
bundle includes `native_profiles.csv` for that path. Two-dimensional cell maps
remain separately measured bins (24 longitudinal × 16 transverse by default).

### Intensity normalization and missing values

Raw leaves fluorescence unchanged. Per-cell max divides the measured profile by
its maximum. Per-cell min–max subtracts its minimum then divides by its range.
Zero denominators map to zero; a constant profile is zero in min–max. Raw values
remain in a separate column on normalized exported source rows. These operations
do not perform background subtraction. LUTs are viewing contrast, not this
quantitative normalization. Check NaN in source/plot data before treating a white
strip as signal: empty bins are missing, while a bright colour can be near-white.

### Spatial aggregation and identities

Demograph sorts cell-observation rows stably by the selected metric, typically
length_um. The guide displays relative length 0–1. A 2D normalized cell heatmap
averages occupied per-cell bins equally; different positions can have different
numbers of contributing cells. It is distinct from a point-density maxima map.

Maxima map offers one raw brightest pixel per cell (first row-major pixel for ties)
or kept detections from saved Filtering foci data. Foci must belong to retained
masks. Principal-axis focus positions can preserve subpixel projection;
medial-axis positions use the nearest measured pixel. Source x/y are retained.
The capsule is schematic; points are not forced inside it. Density uses a 96 × 96
histogram, Gaussian σ=2 bins, normalized to peak 1 with values below 1% transparent;
it is not fluorescence or a probability density normalized to integral 1.

Kymograph requires one source/XY, one verified track-ID group and at least two
time points. The guide can find Tracking masks, filters the chosen ID and
uses minutes with a known interval, otherwise frames. Ordinary labels require
explicit identity-continuity confirmation; there is no implicit tracking. Pole
orientation can still change during rotation and needs review.

## Advanced field recipes

| Figure | X | Y | Value | Other |
| --- | --- | --- | --- | --- |
| Demograph | position | object_key | intensity | Sort length_um; relative-position option for 0–1 |
| Normalized cell heatmap | position | transverse | intensity | Filter the intended frame/population |
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
| figure_data.xlsx | Source rows and Plot data sheets; Replicates sheet when applicable |
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
