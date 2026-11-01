# Simple Analysis: from results to a figure

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 1 November 2026.
[Figure guide](FIGURE_GUIDE.md) · [Methods/export reference](ANALYSIS.md)

## Start with existing results

Run **Segmentation → Analyze** with the required measurements. After successful
completion and final channel merging, BactoMate loads the results and opens the
separate **Analysis** module. You do not need to import spreadsheets manually.
The entire Analysis interface is in English.

On later visits, Analysis finds results using the dashboard workspace, the last
completed analysis, or an existing pipeline path. It can find neighboring analysis
folders from segmentation/filtered-mask paths. **Refresh results** rescans; unchanged
files are cached and unreadable files are reported. If there is no context, open
a workspace or run Analyze first. Multiple output subdirectories are supported.

CSV, TSV, XLSX and XLSM are recognized. Cells, Foci, Tracking, Profiles and Summary
remain separate populations. Known workbook/CSV copies and redundant aggregate
workbooks are avoided by catalogue rules, as are figure-export folders. This does
not guarantee detection of arbitrary duplicate files with unrelated names.

## Example: cell area for conditions X and Y, showing replicates

1. Click **Conditions & replicates…** at the top. Assign each file its condition
   X/Y and replicate R1/R2/R3. Several XYs from one biological replicate should use
   the same replicate name. Use Apply to selected rows for batch assignment; save.
2. In simple controls choose **Cells**, **Violin plot**, **Cell area (µm²)**.
3. Keep **Compare conditions** and **Show replicate means**. Choose the frame/time
   population, then **Draw figure**.
4. The figure opens in its own window. Each violin contains the selected cell
   observations; coloured points are replicate means within condition. A replicate
   keeps its colour between conditions. Use Figure options for order and styling.
5. **Export figure, data & code…** creates PDF/SVG, tables and reproduction scripts.
   The Replicates sheet and `replicate_summary.csv` give counts, means and SD.

A file/XY is not automatically a biological replicate. Means combine the selected
observations of that condition/replicate across its assigned files. This display
does not add significance testing or a hierarchical statistical model. When
cell counts differ between replicates, the pooled cell distribution and the
replicate means answer different questions.

Assignments are saved in **analysis_groups.json** at the catalogue root; source
workbooks are unchanged. Existing condition/replicate columns are recognized.
A nonempty per-file assignment overrides them; blank assignment cells leave the
source information in use. Complete missing assignments before comparing groups.
The button stays at the top in both simple and advanced modes.

## Time and repeated observations

For time-lapses, choose **Frame / time**. The first frame is the default when
frames are available. **All (repeated observations)** pools the selected rows;
the same tracked cell can appear more than once. Those observations are not
independent biological replicates. Use Tracking and a kymograph for one cell's
evolution, rather than interpreting pooled demograph rows as time.

## Guided or advanced figures

**Figure guide…** asks what you want to show, which population/channel to use,
how to display it and what will be drawn. It can find the masks/images already
in the project for spatial plots. Follow the [recipes](FIGURE_GUIDE.md) for
Demograph, Maxima map, Foci count and Kymograph.

**Advanced / MicrobeJ-style controls** keeps all 13 plot types, manual imports,
free axes/groups, exact filters and profile extraction. It is a BactoMate workflow
inspired by MicrobeJ, not a copy of or connection to the Fiji plugin. Advanced
controls do not infer missing tracks, replicate identities or spatial profiles.

## Reopen, edit and start another dataset

Each figure keeps its own data/options. Edit with Figure guide restores that
window's recipe; changing length to width updates axis labels. Export is independent
of screen size, square by default, with dimensions in cm or pixels. Closing an
unsaved/changed figure offers Save/Discard/Cancel. Escape keeps it open.

Before switching experiments, export wanted figures and use **Clear current
session** on the dashboard. Paths, caches, windows and assignments in memory are
cleared; saved results and `analysis_groups.json` stay on disk. Open a new workspace
to work on different data. See [the manual](BACTOMATE_USER_MANUAL.md).
