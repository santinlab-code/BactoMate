# BactoMate command-line and backend scripts

This reference accompanies **BactoMate_Custom_New-Analyses**, reviewed 1 November
2026. Run at the source root using its `venv`. Most researchers can use the GUI;
these scripts support automation and diagnostics. The GUI additionally provides
curation, local recipes, automatic result discovery and guided figure windows.
A standalone CLI call does not imply that every GUI setting/sidecar is applied.

```bash
source venv/bin/activate
python -m bactomate.scripts.<module> --help
```

On Windows use `venv\Scripts\python.exe -m bactomate.scripts.<module> --help`.
Use actual paths in place of the angle-bracket examples. Inspect each --help
before scripting: available switches are script-specific.

## Processing entry points

| Module | Purpose |
| --- | --- |
| convert_nd2_to_tif | Convert supported microscopy input; includes ND2 XY/channel handling |
| batch_process_tiff_sequence | Segment one TIFF/stack with the Omnipose/Cellpose pathway |
| batch_process_folder | Segment/analyze TIFF files in a folder, optionally recursively |
| analyze_cell_areas | Quantify labelled masks, optional FI/foci, workbooks/CSV and visualizations |
| assign_persistent_ids | Assign IDs across a mask stack; continuity still needs scientific review |
| unet_predict_patches / unet_predict_impl | U-Net inference backend |
| unet_train_patches / unet_train_impl | U-Net training backend |

Examples:

```bash
python -m bactomate.scripts.batch_process_tiff_sequence input.tif \
  --model bact_phase_omni --diameter 30
python -m bactomate.scripts.batch_process_folder /path/to/tiffs \
  --model bact_phase_omni --pixel-size 0.108 --detailed
python -m bactomate.scripts.analyze_cell_areas masks.tif \
  --pixel-size 0.108 --detailed --visualization
python -m bactomate.scripts.assign_persistent_ids masks.tif -o masks_cellids.tif
```

The calibration value above is an example, not a default valid for every microscope.
Analyze can add FI/foci using switches such as --fi-image and --run-foci; read
--help for detection-mode/threshold/output controls. Source masks, raw images,
rendered overlays and filtered masks have different roles. Automatic pipeline PNG
previews are disabled; TIFF visualizations and requested measurement exports remain.
GUI Filtering defaults should not be assumed to replace CLI defaults.

## Diagnostics

| Module | Use |
| --- | --- |
| check_tiff_format | Inspect/reshape TIFF layout; read help before any rewrite |
| check_environment | Dependency/backend/device report |
| check_omnipose_pipeline | Model/loader/pipeline readiness, including checkpoint comparison |
| diagnose_flat_model | Investigate flat/incorrect model output |
| inspect_omnipose_checkpoint | Check checkpoint structure and metadata |
| fix_user_model_metadata | Model metadata repair; keep original weights |
| convert_checkpoint_to_plain | Produce compatible state-dict form when appropriate |
| verify_affinity_model | Check affinity model loading |
| patch_omnipose_omni_models | Registry patch helper used in setup workflows |

The launchers run compatibility patches from `setup/apply_all_patches.py`.
Use `python main.py --smoke-test` for the source installation smoke check.
Use `python main.py --version` plus `git rev-parse HEAD` to record custom provenance.

## Documentation and figure reproduction

`generate_bactomate_pdf` is the legacy GUI brochure generator; it does **not**
compile the current Markdown manual. It is not the source for docs/BactoMate.pdf.
The current PDF edition is generated from docs/BACTOMATE_USER_MANUAL.md; the exact
Pandoc command is in [packaging](../../build/README.md#documentation-pdf).

Analysis figure bundles include standalone reproduce.py, reproduce.R and reproduce.m.
Run these from the bundle directory with their listed dependencies. They redraw
saved plot geometry; they are not CLI re-executions of the original segmentation.
PDF/SVG are the defaults; PNG requires an explicit request. See
[Analysis methods](../../docs/ANALYSIS.md) for bundle contents and limitations.

For the complete pipeline, use [the manual](../../docs/BACTOMATE_USER_MANUAL.md).
For install/repair scripts, use [setup](../../setup/README.md).
