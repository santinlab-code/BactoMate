# Foci distance preview and colocalization

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 1 November 2026.
[Manual](BACTOMATE_USER_MANUAL.md) · [Filtering](FILTERING_CURATION.md)

## Prerequisites and purpose

After foci detection, open **Preview distances…** from foci analysis. Choose a
mask/XY, frame, two channels and cell. The overview and selected-cell view use
saved detections. Without a detection CSV, images/cells remain available with an
information message; the preview does not fabricate foci. Multiple XYs are
inspected one at a time, never superimposed into a single field.

The preview shares matching logic with Analyze and updates its selected distance
settings. It does not rerun detection or write analysis outputs.

## Two distance parameters

New settings start at **Max distance = 3 px**, **Threshold = 2 px**; saved sessions
may retain other values. The (?) controls beside them provide help.

1. Max distance sets the radius for candidate partner centers in the other channel.
2. A one-to-one assignment chooses non-overlapping pairs; a focus has at most one
   partner in that channel comparison.
3. Threshold classifies matched pairs as colocalized when their center-to-center
   distance is within that threshold. A pair within the search radius but above
   Threshold remains an invalid/above-threshold match.

For example, a 2.5 px pair can be matched at radius 3 px yet fail a 2 px threshold.
Same cell only, when enabled, restricts eligible partners to the same cell. If
disabled, a valid pair can involve different cells. The selected cell's title
shows **Colocalized** when a valid pair involves it, otherwise **Not Colocalized**.
This distance classification does not by itself demonstrate molecular interaction.

## Read the display

- Cyan and magenta centers distinguish the two foci channels.
- A dotted yellow search circle and green threshold circle depict distances,
  not focus diameters.
- Green links show valid pairs; orange links show matches above Threshold.

The cell zoom includes a pixel grid, a 1 px reference and available µm calibration.
Distances are computed in pixels; multiply by µm/px for physical distance.

## Navigate and adjust contrast

Use **Mask / XY position** for another segmentation, frame controls for time and
previous/next-cell buttons or arrow keys for cells. A simple overview click chooses
a cell; left-drag pans in either view. Wheel zoom around the pointer is limited
to about 5% per event. The unused Home/Pan toolbar icons have been removed.
Changing cells recenters the selected-cell view; LUT/threshold changes preserve
the region being observed.

Visible checkboxes let phase and several fluorescence channels appear together.
**LUT channel** selects which histogram to edit, rather than which image is visible.
Move the histogram Min/Max lines or use Auto LUT (current-frame percentiles 1 and
99.5). Each image retains its own range while observing that position. Channels
are added and clipped for display. LUTs are open directly, without a collapsed
panel. These adjustments do not change image pixels, measurements or matching.
