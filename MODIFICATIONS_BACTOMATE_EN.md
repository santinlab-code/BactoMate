# BactoMate — summary of changes

Development version prepared for team testing on October 27, 2026.

Comparison baseline: BactoMate 2.9.5, commit `2dfd181` from
`santinlab-code/BactoMate`. The changes below are available in the GitHub branch
`test/bactomate-optimisations`.

## 1. File Conversion: ND2 files with multiple XY positions

**Before:** conversion did not correctly extract every position from one ND2 file.

**Now:** every XY position is exported separately with its channels. File names
contain `XY001`, `XY002`, and so on. Existing conversion options for time, Z,
channel selection, cropping, and corrections are preserved. Calibration is retained,
and Nikon PH3 phase-channel recognition has been corrected.

For the reference file, **3 positions × 3 channels = 9 TIFF files**. The channels
are GFP, mCherry, and phase. Pixel comparison against the ND2 confirmed that the
exports match their sources.

For time-lapse data, time is retained in each position/channel TIFF stack. This was
verified with synthetic data. The reference ND2 has only one time point, so it does
not by itself validate real time-lapse ND2 files.

## 2. Segmentation: cell outlines

**Before:** multicolor fills could obscure cell details.

**Now:** the preview displays outlines in a user-selected color. The color is saved
and used by newly exported outline images. Changing the color does not rerun
segmentation or alter masks or measurements.

Display behavior was checked on all three reference positions. This validates the
display function, not the biological accuracy of every segmented cell.

## 3. Filtering: manual curation

Users can select already detected cells or foci and:

- keep them even when automatic filters reject them;
- exclude them from the selection;
- clear the manual decision and return to the filter result.

These decisions affect the preview and exported filtered results. They do not draw
new objects or delete the original masks. Decisions apply to the current frame;
foci decisions also apply only to the relevant channel.

Decisions are stored in a `.curation.json` file beside the mask. Keep this file
with the mask to restore decisions later. If new segmentation changes the mask,
old decisions are not automatically applied to new cell identifiers.

## 4. Filtering: cell table

A table lists cell identifiers, selection status, area in square pixels, and
position. Multiple rows can be selected, and cells can also be selected in the
image. Double-clicking a table row centers the image on that cell. The existing
foci table selects foci from the active channel.

## 5. Filtering: counts and history

The **Cell table / Manual selection / History** panel displays selected cells versus
the total count. The history records filtering steps, before/after counts, count
changes, parameters, and associated manual decisions. Per-channel foci counts are
recorded when data are available.

Displayed counts apply to the current frame, not the entire movie. The history
documents the steps; it is not a restore button for an earlier state.

## 6. Filtering: independent per-channel settings

**Fix:** switching channels could leave the same values in the controls and save
them for the wrong channel.

**Now:** GFP and mCherry each retain their own thresholds and checkbox states.
Changing the channel under **View** stores values for the channel being left and
loads values for the selected channel, even before Apply is clicked. Analysis uses
the settings assigned to each channel.

## 7. Filtering: reusable parameter files

**Save filter settings…** creates separate JSON files. **Import filter settings…**
loads them individually for a future analysis. **Filter File/Folder** also creates
them automatically beside exported filtered masks.

Example suffixes for the reference file:

| File | Contents |
| --- | --- |
| `.filter_settings.cells.json` | Phase cell filters, including calibration |
| `.filter_settings.foci_01_CT_16bits_GFP.json` | GFP foci filters |
| `.filter_settings.foci_02_CT_16bits_mcherry.json` | mCherry foci filters |

The prefix depends on the exported mask name, and the numbers depend on channel
order. The channel name is also stored inside the file.

Importing a GFP file does not change mCherry or cell settings. Keep channel names
consistent between analyses. Older JSON files containing all settings remain
importable. Incompatible files are rejected without replacing current settings.

The files contain thresholds and filter activation states, not manual decisions
for individual objects. Manual decisions stay in the curation files associated
with the original images.

## 8. Foci analysis: initial colocalization values

The new defaults are:

| Parameter | Before | Now |
| --- | --- | --- |
| Max distance | 8 px | **3 px** |
| Threshold | 4 px | **2 px** |

Max distance is the radius used to search for a partner in the other channel.
Pairing is one-to-one. Threshold then determines whether a matched pair is counted
as colocalized based on the distance between foci centers. A saved session may
retain its own values.

## 9. Foci analysis: distance preview

**Preview distances…** opens an overview and a zoomed view of one cell. Users can
select the cell, frame, two channels, and an available background image (phase or
fluorescence).

- Foci centers: cyan for A and magenta for B.
- Dashed yellow circle: Max distance radius; green circle: Threshold.
- Green line: colocalized pair; orange line: matched pair above Threshold.

In the zoomed view, the grid corresponds to one image pixel and a white square
represents 1 px. Calibration in µm is shown when available. The circles represent
distances, not foci diameters.

Parameters changed in this preview update Foci analysis. The preview uses the same
pairing calculation and Same cell only option as the analysis, without rerunning
detection or writing analysis results.

Without detection CSV data, images and cells remain visible and an information
message is shown. No artificial foci are added.

## Verification and test limitations

The latest complete automated run produced **542 passing tests and 5 skipped
tests**. A focused preview check also passed after the final adjustments.

The reference file is `2025-10-02-Snaps-AP-GL2430-GA178-Cd16.nd2`. Real-data tests
covered export of the nine TIFF files, outlines for all three positions, curation
and export on the first position, and display of the distance preview and calibration.

Foci filtering, independent settings, and colocalization pairing behavior were
tested with controlled data. Foci detection, biological colocalization, and
fluorescence measurements on the real file still need evaluation by the team.
This document does not certify their scientific quality.

## Additional documentation

- `GUIDE_TEST_BACTOMATE_EN.md`: installation and test workflow.
- `GUIDE_TEST_BACTOMATE_FR.md`: French version of the test guide.
- `MODIFICATIONS_BACTOMATE_FR.md`: French version of this summary.
- `docs/ND2_MULTIPOINTS_FR.md`
- `docs/SEGMENTATION_CONTOURS_FR.md`
- `docs/FILTERING_CURATION_FR.md`
- `docs/FILTERING_PRESETS_FR.md`
- `docs/FOCI_DISTANCE_PREVIEW_FR.md`
