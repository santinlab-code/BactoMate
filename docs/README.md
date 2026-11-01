# Documentation index

These guides describe **BactoMate_Custom_New-Analyses**, reviewed on 1 November
2026 against code commit `811d5b6`. The package version remains 2.9.5; the branch
and Git commit identify the custom build. All topic guides are in English.
Only the testing guide and consolidated change summary also have French editions.

## Install and start

| Document | Use it for |
| --- | --- |
| [Project README](../README.md) | Correct branch, ZIP/clone and first launch |
| [Setup](../setup/README.md) | Python 3.11, macOS/Windows, venv updates and repairs |
| [Windows installation](INSTALL_AND_LAUNCH_windows.md) | Windows prerequisites and dependency troubleshooting |
| [Testing guide (EN)](../GUIDE_TEST_BACTOMATE_EN.md) / [(FR)](../GUIDE_TEST_BACTOMATE_FR.md) | Test a new installation on your own images |

## Use the application

| Document | Use it for |
| --- | --- |
| [User manual](BACTOMATE_USER_MANUAL.md) / [PDF edition](BactoMate.pdf) | Full pipeline, project/session state and shared controls |
| [Multiposition ND2](ND2_MULTIPOINTS.md) | XY/channel export, metadata and file naming |
| [Segmentation previews](SEGMENTATION_CONTOURS.md) | Contours, colour, detached image and LUTs |
| [Filtering curation](FILTERING_CURATION.md) | Cells/foci, tables, selection, exclusion and manual objects |
| [Filtering settings](FILTERING_PRESETS.md) | Independent XY/channel recipes and portable JSON files |
| [Filtering review and outputs](FILTERING_REVIEW.md) | Batch selection, saved results and duplicate-file audit |
| [Foci distance preview](FOCI_DISTANCE_PREVIEW.md) | Pairing, colocalization, display and navigation |
| [Simple Analysis](NEW_ANALYSIS.md) | Automatic data loading, conditions and replicates |
| [Figure guide](FIGURE_GUIDE.md) | Step-by-step figures, intensity choices and figure windows |
| [Analysis methods and exports](ANALYSIS.md) | All 13 figure types, coordinates, sampling and code reproduction |

**Analyze** in the Segmentation workflow computes measurements. The separate
**Analysis** module visualizes those results. A successful Analyze run loads its
final results and opens Analysis automatically. Start a different dataset with
**Clear current session** on the dashboard; saved files are retained.

## Changes, maintenance and provenance

| Document | Use it for |
| --- | --- |
| [Custom changes (EN)](../MODIFICATIONS_BACTOMATE_EN.md) / [(FR)](../MODIFICATIONS_BACTOMATE_FR.md) | Current cumulative behavior, replacing the former running diary |
| [Release notes](RELEASE_NOTES.md) | Custom milestones and test evidence |
| [Script reference](../bactomate/scripts/README.md) | CLI tasks, model diagnostics and GUI backends |
| [Packaging](../build/README.md) | Build a custom macOS/Windows distribution |
| [Paper data](PAPER_DATA.md) | Upstream research data and attribution |

The retired French topic guides have been replaced by the English files linked
above. PNGs under `docs/images/` are documentation illustrations, mostly synthetic;
they are not newly generated pipeline results. Current bundles export PDF/SVG by
default. Existing result PNGs are not deleted automatically.
