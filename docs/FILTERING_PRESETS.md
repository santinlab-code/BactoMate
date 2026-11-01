# Filtering settings: XY recipes and portable presets

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 1 November 2026.
[Curation](FILTERING_CURATION.md) · [Batch review](FILTERING_REVIEW.md)

## Local independence and initial inheritance

Each visited mask/XY retains its own cell filters, pixel calibration and foci
settings for every channel. On the first visit to a new mask, the previous recipe
is copied as a starting point. Later edits are independent. Revisiting an existing
XY restores its recipe. Changing GFP/mCherry saves/restores channel values even
without Apply first. Filtering also keeps display LUT ranges per mask/channel;
those ranges are separate from scientific threshold settings.

New Filtering recipes enable **Exclude cells at borders** and **Exclude fully
outside**. Explicit saved/imported values remain respected. Other independent
Analyze/CLI controls do not necessarily use these defaults. Check calibration
against each image's metadata; a convenient inherited value is not evidence
that two acquisitions used the same pixel size.

Local recipes and manual curation are stored in the source mask's `.curation.json`.
Do not copy object decisions to unrelated segmentations.

## Portable settings files

Use **Save filter settings…** / **Import filter settings…** above the filters.
The duplicate controls formerly in the left interface are removed. Export creates
one cells JSON and one named-channel foci JSON. Filter File/Folder also writes
them beside each exported filtered mask. Typical names are:

```text
<filtered-mask>.filter_settings.cells.json
<filtered-mask>.filter_settings.foci_01_GFP.json
<filtered-mask>.filter_settings.foci_02_mCherry.json
```

Exact prefixes, numbers and sanitized channel names vary. Channel identity is
also in the file contents. Keep channel names consistent between experiments.
A cells preset changes cell settings; a GFP preset changes GFP only, leaving
mCherry/cells unchanged. Presets contain enabled flags, thresholds and applicable
calibration, not object-specific choices or history. Verify the new image's
metadata/calibration after importing.

Legacy combined presets remain importable. The supported format identifies
`bactomate-filter-settings`, version 1. Invalid/incompatible files are refused
without replacing current settings. Finish a filtering calculation before importing.

## Example

Tune XY1, then visit XY2 and adjust it. Return to XY1 to verify independence.
Export the GFP preset from XY1. Import it into a compatible new dataset and check
GFP thresholds, then confirm that mCherry and cell parameters were preserved.
Export each selected mask using the batch list: its own recipe should be recorded,
not whichever recipe happens to be visible at the end.
