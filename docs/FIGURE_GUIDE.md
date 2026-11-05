# Figure guide: practical recipes

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 5 November 2026.
[Simple Analysis](NEW_ANALYSIS.md) · [Methods and exports](ANALYSIS.md)

## Four steps

Click **Figure guide…** in Analysis:

1. **Question:** compare a measurement, relate two metrics, show a demograph,
   map cell fluorescence, locate maxima, count foci per cell, or follow a cell
   through a time-lapse.
2. **Population:** choose data/metric, condition, frame and, for spatial figures,
   channel and all matching XYs or one sample. Conditions & replicates is available
   here and remains at the top of the main Analysis view in both modes.
3. **Appearance:** choose plot type, relevant normalization, coordinate method,
   sampling and orientation. Only relevant choices are shown.
4. **Review and draw:** verify population and settings before drawing. Spatial
   extraction runs in the background and uses existing project images/masks.

Filtered masks are preferred; unfiltered sources are reported in the review.
Calibration is read from mask/original-image metadata, then fluorescence metadata;
enter a fallback µm/px if neither supplies it. The guided path does not open a
manual table/file-import dialog. External imports remain in advanced controls.

## Compare cell area between conditions

Set Conditions & replicates first, giving XYs of one biological replicate the
same name. Choose cell measurement comparison, Cells, Cell area (µm²), the desired
frame, and Violin plot or Box plot. Enable condition comparison and replicate
means. Cell distributions are distinct from coloured replicate means. No automatic
significance test is added. See [the complete example](NEW_ANALYSIS.md).

## Demograph: fluorescence along a cell population

Choose the demograph question. In Population, select the channel, condition, frame
and XY population. The guide extracts measured profiles from the project's mask
and fluorescence images; a morphology spreadsheet alone is not enough.

Keep **Automatic — follow curved cells** for a mixture of straight and vibrioid
cells. It follows a smoothed centerline through both caps when curvature is
detected and uses a straight axis for near-straight cells. Explicit principal-axis
and medial-axis choices remain available. Ambiguous curved/branched masks are
refused; inspect and curate the reported cell. Choose geometric orientation
unless a deliberate brighter-pole alignment is appropriate. Brighter pole places
the end with greater mean terminal-quarter signal at left/top; it does not identify
an old/new pole and changes the apparent population pattern.

The default **Length-scaled columns — cells ordered by length (VDemo)** puts one
cell observation in each column, shortest to longest. Its profile is centered at
zero and displayed with its measured centerline length. Y is centered axial
distance divided by half the longest cell's length; the longest cell spans −1…1.
The growing outer envelope therefore retains the population's length differences.
Colour shows **Fluorescence intensity** by default, in raw measured units. Choose
**Local cell width (µm)** to reproduce the second reference panel: colour then
shows mask width perpendicular to the local axis, with no intensity normalization.

The earlier **Normalized rows — each cell has equal displayed length** layout
remains available, with one cell per row and longitudinal position 0–1. Both
layouts use the sampling/normalization choices below. Counts are cell observations,
not bins. First frame avoids repeated film observations; All frames intentionally
includes them. A demograph is not a time-lapse kymograph. Geometric orientation
alone does not align a particular biological pole across cells.

### Choose an intensity scale

Let I be a cell's measured profile, m its minimum and M its maximum.

| Menu choice | Displayed intensity | What is retained/lost |
| --- | --- | --- |
| Keep absolute fluorescence | I | Measured brightness differences between cells; acquisition/background must be comparable |
| Scale each cell to its maximum | I/M | Pattern and baseline relative to its peak; absolute brightness is lost |
| Scale each cell from 0 to 1 | (I−m)/(M−m) | Within-cell contrast; minimum/background offset and absolute brightness are lost |

Example profile **10, 20, 50** becomes **0.2, 0.4, 1** with max scaling, and
**0, 0.25, 1** with min–max. A constant profile becomes 0 in min–max; a zero
denominator also maps to 0. Missing values stay missing. Raw values remain in the
export when normalization is applied. These operations are not background
correction. Display LUTs in preview windows are a separate operation and do not
change the quantitative profile.

### Choose sampling and read missing strips

Default **24 segments (direct measurements)** averages the contributing pixels
in each longitudinal segment. Empty bins remain NaN. More segments can leave gaps
when cells have few longitudinal pixels; bin count is not optical resolution.
Bright near-white colormap values and white missing areas must be distinguished
using the colour scale and exported plot_data.csv.

**Native resolution → 24 positions** first measures means at approximately
one-pixel longitudinal intervals and then linearly interpolates the measured means
onto 24 common positions. Edge positions hold the first/last measured mean.
The export adds **native_profiles.csv** to preserve the native measurements.
Resampled positions are labelled separately and have no invented contributing
pixel counts. This option improves a common display grid without adding image
resolution. The separate 2D cell-map bins are not changed into native profiles.

These 24 segments concern Analysis profiles, not the model's cell segmentation.

## Mean fluorescence on a normalized cell

Choose **Map fluorescence on a normalized cell**, then the channel, condition,
frame and XY population. Keep the automatic cell-shape method. In Appearance,
choose raw or per-cell normalized fluorescence, the colour map, and **black**
or **white** background. The defaults are raw fluorescence, turbo and black.
Generate separate figures for different conditions when comparing distributions.

Every retained cell is straightened onto the same capsule: relative length 0–1
and relative width −0.5…0.5. Signed lateral distance is divided by the local
half-width, then mapped into the reference capsule's cap geometry. This follows
curved cells instead of flattening their bends onto a global straight axis.
The guide samples a 64 longitudinal × 32 transverse grid by linear interpolation
within measured pixel support; it does not extrapolate or fill missing values
with zero. This display grid adds no optical resolution. At each position the
heatmap is the equal-weight mean of cells contributing there, not a pooled pixel
mean. The number of contributors can vary; inspect `cell_coverage.csv` in exports.

The outline is a common schematic shape, not the mean measured cell boundary.
Keep acquisition/background comparable before comparing raw brightness. Display
LUT changes do not alter these measurements. Background and palette remain
editable in Figure options. Advanced controls retain rectangular cell maps.

## Maxima on a normalized cell

Choose the maxima-location question and a channel/population. Select one source:

- **Brightest pixel in each cell:** one raw-image maximum per retained cell;
  ties use the first row-major pixel. This is not foci detection.
- **Kept detected foci:** saved filtered foci for that channel. Save Filtering
  first. Foci outside the retained masks are excluded from this spatial view.

Keep **Automatic — follow curved cells**. Axial position follows centerline arc
length through both caps; lateral position uses the local normal and half-width
before mapping into the reference capsule. Subpixel foci use local interpolation
of that nonlinear coordinate field. A pole focus therefore stays close to the
pole axis when a vibrioid cell is straightened; a genuinely off-axis focus keeps
its signed lateral offset. No focus is deliberately snapped onto the centerline.

Raw x/y, `axis_position_um`, signed `normal_distance_um`, cell metrics, actual
coordinate method and geometry version remain exportable. The relative capsule
is schematic; its coordinates do not preserve every physical distance. Density
defaults to a 96 × 96 histogram smoothed with a Gaussian of σ=2 bins and scaled
to peak 1. The displayed kernel is masked outside the capsule; values below 1%
of peak are transparent. This does not move the individual points. Density is
relative point density, not fluorescence or probability. Figure options controls
point visibility, density resolution/smoothing, background and palette.

Rebuild spatial figures from masks/images with the guide to use these coordinates.
Old exported coordinates cannot be corrected from a morphology table alone.

## Number of foci per cell

Choose the foci-count question and a **per-cell count** column, for example a
channel-specific `num foci` field. Percentages use all selected cells per condition,
including zero foci. A foci-only table cannot provide that denominator. Use the
frame choice to avoid pooling repeated observations unintentionally.

## Time-lapse kymograph

Choose **Follow one cell through a time-lapse (kymograph)**. Select one sample/XY
and channel, a tracked-mask export found in `_tracking`, and one cell/track ID.
Confirm **I verified that this ID follows the same cell over time**. Source labels
are allowed only after explicit continuity verification; changing labels should
be linked/reviewed in Tracking first.

Set the frame interval if known. The guide uses the selected ID’s available frames. The plot needs at least two observations of that
identity. X is relative longitudinal position 0–1; Y uses minutes when the frame
interval is available/supplied, otherwise frames. Frame indices and track/source
identity remain in the export. Geometric orientation does not guarantee pole
continuity for rotating cells; inspect orientation before pole-specific inference.

## Independent windows and Figure options

Each draw opens a movable window in front of BactoMate. Each window keeps its own
data, recipe, options and exports. The live canvas fills the window; export uses
an off-screen copy and does not resize the live canvas or overlap older figures.
The default export is square, **15.24 × 15.24 cm**. A normalized capsule keeps an
appropriate internal aspect ratio within that page.

**Figure options…** includes:

| Panel | Controls |
| --- | --- |
| Labels / axes | Title, X/Y labels, automatic/custom bounds, X-label rotation, title/grid/legend visibility |
| Categories | Move up/down, display names/colours, box/violin X spacing and width |
| Appearance | Font and point size, opacity, line width, box outliers, maxima points, density resolution/smoothing, black/white background, colormap/colour bounds |
| Export size | Square lock, width/height in cm or pixels, raster DPI |

Apply redraws only that figure. Category spacing controls chiefly apply to
boxes/violins; numeric X values retain their scientific meaning. Pixel dimensions
are converted using the chosen DPI; vector pages use the corresponding physical
size. Screen dimensions are independent of exported dimensions.

**Edit with Figure guide…** restores the window's scientific settings and retains
publication options. Changing a metric clears stale axis-label overrides, so a
width plot does not keep a length label. Compatible advanced metric figures can
also reopen the guide from their actual rows. Expert spatial figures without a
guided recipe retain Figure options. Edit a figure with its original project open;
its existing export remains usable after project changes.

Escape keeps figures visible. The close cross offers Save / Discard / Cancel
for new/changed figures; an unchanged exported figure closes directly. Save writes
the complete bundle; cancelling folder selection keeps the window open. Clear
current session closes figures internally without individual prompts, so export
wanted figures before resetting.

## Export and reproduce

**Export figure, data & code…** produces PDF/SVG by default, CSV/XLSX source and
plot data, metadata/provenance and Python/R/MATLAB scripts. Optional replicate
summaries and native profiles are included when relevant. Length-envelope figures
add a cell-order/length table; normalized maps add a contributing-cell matrix.
Automatic PNG generation
is off. Explicit manual PNG saving remains available; old PNG files are not removed.
The scripts redraw computed geometry and do not repeat original analysis. Python
execution is tested; native R/MATLAB execution and native macOS window behavior
still need local validation. See [the export reference](ANALYSIS.md#export-bundle).

## Illustrations

These screenshots use **simulated measurements**, not experimental evidence.
Some show an earlier control arrangement; the current text above defines behavior.

![Four-step guide on synthetic data](images/figure-guide-example.png)

![Synthetic population demograph](images/analysis-demograph-example.png)

![Synthetic normalized maxima map](images/analysis-maxima-example.png)

![Independent figure window](images/free-figure-window-example.png)

![Category order, labels, colours and spacing](images/figure-category-options-example.png)
