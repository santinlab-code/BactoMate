# Compare segmentation on macOS and Windows

Updated **3 November 2026** on **BactoMate_Custom_New-Analyses**.
[Setup](../setup/README.md) · [Manual](BACTOMATE_USER_MANUAL.md)

## What the update harmonizes

Omnipose now uses one native-resolution, tiled, single-plane inference function
for the single-image preview, folder preview and saved-file/batch processing.
Normalization, channels, diameter, thresholds, tiling and reconstruction options
are explicit. Display reduction no longer reduces Omnipose inference resolution.
Diameter 0 uses the backend's automatic/default behavior consistently. Cellpose-SAM
and U-Net retain their separate backend workflows.

The former file export used a different tiling choice from the preview. Counts
from new file processing can therefore differ from old exported results even on
the same computer. This change aligns the two workflows; it does not force the
historical count of 464 cells or establish which segmentation is biologically best.

The preview now respects **Use GPU**. It previously forced GPU on internally.
This checkbox is also available in the embedded Cell segmentation controls.
For GPU calculations, cuDNN benchmarking and TF32 are disabled and deterministic
cuDNN kernels are requested. CPU comparison uses one PyTorch thread and disables
the model's MKLDNN conversion. MPS and CUDA can still differ numerically; equal
settings alone are not a guarantee of identical masks on different hardware.

## Common package baseline

The requirements and installer verification use these versions on both platforms:

| Package | Version |
| --- | --- |
| Omnipose | 1.1.4 |
| Cellpose-Omni | 0.9.1 |
| DBSCAN | 0.0.12 |
| PyTorch / torchvision | 2.11.0 / 0.26.0 |
| NumPy / SciPy | 1.26.4 / 1.17.1 |
| scikit-image / scikit-learn | 0.24.0 / 1.9.1 |
| numba / edt / fastremap | 0.68.0 / 3.1.2 / 1.21.0 |
| opencv-python-headless / ncolor | 4.11.0.86 / 1.5.3 |
| tifffile / nd2 | 2026.3.3 / 0.12.0 |

CPU/CUDA build suffixes can differ while matching the same PyTorch release.
The Windows and optional CUDA installers preserve the exact torch/vision/audio
release pins. DBSCAN 0.0.12 wheels are available for Windows x64, macOS Intel/ARM
and Linux. These are a shared segmentation baseline, not a lock of every optional
Training, Tracking or Post-processing dependency.

## Update an existing installation

Download/update this branch's source, then rerun the installer in its final folder.
Updating only Python source does not update the libraries in an existing venv.

macOS:

```bash
./setup/macos/install.sh
./launch_gui.sh
```

Windows:

```bat
install_windows.bat
launch_windows.bat
```

Both installers create a fresh environment and protect an existing one as
`venv.previous`. A leftover backup stops another reinstall; rename/archive it
before trying again. Windows retains that backup after success; macOS removes
its backup after successful validation. Keep microscopy data separate from source
replacement and use the newly generated launcher, not a shortcut to an old folder.

Both installers check the installed baseline and run an actual small CPU
segmentation with diameters 30 and 33 before accepting success. This tests loading,
inference, fractional rescaling and output shape; it is not a scientific test of
cell accuracy. Windows writes the baseline, smoke result and pip freeze to
`Logs/install_last.log`. macOS records the installation transcript in
`Logs/install.log`. Runtime version mismatches are also reported at startup.

To check manually in the active environment:

```bash
python -m bactomate.scripts.check_environment --segmentation-only
python -m bactomate.scripts.check_environment --segmentation-smoke-test
```

On Windows, use `venv\Scripts\python.exe` in place of `python` if not activated.
The smoke test uses the built-in checkpoint cache and may populate it if missing.
It does not write mask/result image files.

## Compare the same experiment

1. Use the same converted phase TIFF, XY, frame and checkpoint on both computers.
   Keep morphology filtering out of the initial comparison. Match diameter,
   Flow/Mask thresholds, DBSCAN and all other explicit settings.
2. **Uncheck Use GPU on both machines**, then click Re-detect and process the file.
   This is the CPU reference comparison. Do not compare a previous GPU preview
   or a filtered count to the newly computed source-mask count.
3. Compare the new logs/session JSONs. Confirm package versions, image shape,
   `pixels_sha256`, checkpoint SHA-256, parameters, actual device and recovery mode
   before comparing counts/masks. Assess the retained boundaries on the images.
4. After the CPU comparison, GPU can be re-enabled for speed. Compare MPS/CUDA
   outputs separately; do not assume bit-for-bit equality across accelerators.

Both **Help → Check environment** and the startup log include package versions.
New session JSONs include `environment` and the latest successful preview's
`last_preview_segmentation` when present. File/batch inference records appear in
the GUI log as `[segmentation input]` and `[segmentation result]`, including input
pixels, loaded weights, actual device, effective parameters, count and mask hash.
Source-code hashes describe the installed/patched backend files; differing hashes
can also reflect platform line endings, so inspect them before inferring a method
change. Raw file metadata differences do not imply different pixels.

Preview cache keys now include pixels, checkpoint contents, environment and engine
revision. **Clear Cache** also removes that input's disk preview entries;
**Re-detect** bypasses cached results. Session reset clears the in-memory latest
preview report. No extra per-image diagnostic sidecars or PNGs are generated.

## Corrected failure cases

A reproducible Cellpose-Omni rounding error at diameter 33 produced a 1461 × 1461
field for a 1462 × 1462 allocation. The shared function retries that shape error
with native-grid resampling, preserving the chosen diameter and original image
extent. It records `resample=true` for the recovered calculation. It never crops
image borders to hide the mismatch.

An unrecoverable inference/read error now aborts the run instead of inserting an
empty mask and announcing success. No new mask stack is written for that failed
run. Pre-existing results remain on disk; the failure is reported. A successfully
calculated empty mask is still a valid zero-detection result.

Preview controls disconnect their main-panel listeners when destroyed. Changing a
parameter after closing/replacing an image must no longer access a deleted
QDoubleSpinBox or QCheckBox.

The update does not overwrite saved scientific settings. For example, the supplied
sessions used optimized Spotiflow thresholds on Mac versus a manual 0.65 on Windows,
and colocalization thresholds of 3 versus 2 px. Match these explicitly for foci
comparisons; they do not explain the initial cell-segmentation count difference.

## Validation scope

Regression checks cover shape recovery without lost pixels/changed diameter,
failed runs without mask writing, native-resolution preview/export equivalence,
control deletion, CPU selection, cache fingerprints and installer baseline checks.
A local CPU run on the retained laboratory validation TIFF (1608 × 1608) completed
at diameters 30 and 33; the latter reproduced and recovered the logged shape error.
The validation image is the earlier laboratory fixture, not a byte-verified copy
of the newly reported Mac/Windows input. Native macOS/MPS and Windows/CUDA runs
still need the comparison above; no equal-cell-count claim is made for them.

The bundled phase/fluorescence checkpoint hashes are checked before built-in
loading. A mismatched file is reported without deleting it; restore the checkpoint
shipped with this branch or load different weights explicitly as a user model.

The optional shell CUDA helper uses the pinned cu128 build and checks driver
capability (CUDA 12.8 or newer). With an older/missing NVIDIA driver it keeps
the installed CPU/MPS stack; it does not downgrade PyTorch to obtain an older
CUDA wheel. Native Mac operation uses MPS or CPU, without this NVIDIA helper.

Validation on 3 November: **626 passed, 5 skipped** in the full Linux suite,
with two existing warnings; the actual CPU installer smoke test passed at both
diameters. Native macOS/Windows validation remains pending.
