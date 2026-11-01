# Multiposition ND2 conversion

Current custom branch: **BactoMate_Custom_New-Analyses**. Reviewed 1 November 2026.
[Manual](BACTOMATE_USER_MANUAL.md) · [Index](README.md)

## Export every XY and channel

File conversion automatically processes all XY positions in an ND2; no additional
multiposition switch is required. With **Save channels separately**, every XY and
channel produces a TIFF. Example for phase and GFP over two positions:

```text
Tif_files/
  sample_XY001_phase.tif
  sample_XY001_fi_GFP.tif
  sample_XY002_phase.tif
  sample_XY002_fi_GFP.tif
```

Exact channel-role suffixes depend on FI/Foci assignments. A channel used for both
can include `_fi_foci_`. Preserve the sample/XY part for later name matching.
Single-position inputs retain conventional names without an added XY suffix.
Combined-channel mode produces one multichannel TIFF per XY instead.

Each TIFF retains the selected time range. Selecting one time point applies to
all XYs. Z-plane/projection choices, cropping and correction settings apply at
each XY; one crop rectangle is reused, so check its suitability at all positions.
Calibration/time metadata is retained when available. Nikon PH3 phase channels
are recognized even when phase is not the first channel.

## Preview and check

The conversion preview shows the first XY; it is not proof that every exported
position is correct. Start with a small copy, no crop/corrections and separated
channels. Verify file count = XY count × channel count, then inspect each field,
channel, frame count, bit depth and pixel size in BactoMate/Fiji. Confirm all
channels of one XY align before segmentation or colocalization.

A real three-XY/three-channel/one-frame ND2 previously produced nine 1608 × 1608,
16-bit TIFFs with pixel identity and calibration checked against the source.
Simulated tests cover dimension orders, singleton/absent axes, time/Z selection,
Z projection, crop, combined/separated channels and metadata. This single-time
real dataset does not validate every real ND2 time-lapse or reader variant.
