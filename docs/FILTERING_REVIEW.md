# Filtering: batch export and generated-file review

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 1 November 2026.
[Curation](FILTERING_CURATION.md) · [Settings](FILTERING_PRESETS.md)

## Select XYs to export

The preview's Mask / XY position chooses the current image; it does not reduce
the intended batch to that single mask. **Filter File/Folder** reopens the full
available-mask list, with an indication of existing results, after single-XY
navigation. Select the masks to export and review completion status.

Raw and filtered versions of a mask are grouped. When the original exists,
Filtering starts from it so previously excluded objects remain recoverable.
Each mask uses its own saved cell/calibration/channel recipe. A never-visited
mask starts with the latest recipe; revisiting a known mask preserves its own
choices. Processing a batch must not overwrite the active preview's recipe.

## Output roles

| File | Purpose |
| --- | --- |
| Original integer mask TIFF | Detected source labels; needed for reversible exclusion |
| `.curation.json` | Decisions, annotations and mask/channel recipes |
| Filtered mask TIFF | Retained cells plus valid manual cell annotations |
| Filtered foci CSVs | Retained channel-specific detections/manual foci |
| `.filter_settings.cells.json` | Portable cell settings |
| `.filter_settings.foci_*.json` | Portable settings for the named channel |
| Visualization TIFFs | Visual QC, not the label source |
| Analysis workbooks / optional CSVs | Measurements after Analyze |

Use saved filtered outputs for downstream Analyze and kept-foci figures. The live
preview alone is not an exported filtered dataset. Keep sources and sidecars
together; a settings preset cannot reconstruct the original labels or individual
curation choices.

## Automatic PNGs are disabled

The pipeline no longer writes companion PNG previews. Default figure bundles
and reproduction scripts produce PDF/SVG. Existing PNGs are not deleted in bulk,
and explicit manual figure PNG saving remains possible. PNG illustrations in
the documentation are separate assets and remain in the repository.

## Audit potential duplicates

**File → Inspect generated files…** reads the project, groups files by role,
checks binary-identical contents and compares analysis CSVs to corresponding
XLSX sheets. The report can be saved as JSON. It never deletes results.

Raw/filtered masks have separate purposes even when a particular run changes
nothing. Aggregate workbooks intentionally collect individual results. **Also
save CSV** is off by default; enabling it deliberately copies workbook data into
text files for downstream tools. The Analysis catalogue avoids known copies by
naming and role, but arbitrary renamed files still need review. Treat the audit
as evidence for your own file management, not as an automatic cleanup operation.
