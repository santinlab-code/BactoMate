# BactoMate Custom

BactoMate Custom is a bacterial microscopy workflow for conversion, segmentation,
filtering and manual curation, fluorescence/foci measurements, tracking and figures.
This repository documents the laboratory customizations built on BactoMate 2.9.5.

**Active custom branch: [`BactoMate_Custom_New-Analyses`](https://github.com/santinlab-code/BactoMate/tree/BactoMate_Custom_New-Analyses).**
The former `BactoMate_Custom_V1` and `BactoMate_Custom_Analyses` branches were
removed from GitHub. Use this active branch for installation and further work.
The package may still report version `2.9.5`; record the Git commit to identify
this custom build. Documentation updated on **5 November 2026**; see the branch commit for the custom revision.

## Install this custom version

Use the active branch's source, rather than an upstream release app: upstream
DMG/Windows downloads do not establish that these custom features are included.

```bash
git clone --branch BactoMate_Custom_New-Analyses --single-branch \
  https://github.com/santinlab-code/BactoMate.git BactoMate_custom
cd BactoMate_custom
```

Without Git, [download the branch ZIP](https://github.com/santinlab-code/BactoMate/archive/refs/heads/BactoMate_Custom_New-Analyses.zip),
extract it, and rename the extracted folder `BactoMate_custom` if desired.
Keep the folder containing `main.py`, `requirements.txt` and `launch_gui.sh`.

### macOS

Use Python 3.11 and open Terminal in that folder:

```bash
chmod +x setup/macos/*.sh launch_gui.sh
./setup/macos/install.sh
./launch_gui.sh
```

If the folder is directly under your home directory, subsequent launches are:

```bash
cd ~/BactoMate_custom
./launch_gui.sh
```

Create the virtual environment in its final folder. Moving a `venv` from an old
installation can leave absolute paths pointing to the old code. Recreate it with
the installer after moving/replacing the project. See [setup](setup/README.md).

### Windows

Use 64-bit Python 3.11 and a user-writable folder. In Command Prompt:

```bat
setup\windows\install.bat
launch_windows.bat
```

See the [Windows guide](docs/INSTALL_AND_LAUNCH_windows.md) for runtime requirements
and dependency repairs. GPU acceleration is optional; CPU processing is supported.

## Current workflow

1. **File conversion:** export each ND2 XY and channel, preserving calibration.
2. **Segmentation → Filtering → Analyze:** detect cells/foci, curate each XY,
   save filtered results and measure the retained objects.
3. **Analysis:** results load automatically after Analyze. Assign conditions and
   replicates, then use the simple controls or Figure guide to draw figures.
4. **Tracking:** link time-lapse cell identities before making a kymograph.

Detached image windows keep their LUT controls on the right, support mouse zoom
and pan, and offer recentering and position sliders. Filtering supports object
selection, reversible exclusion and manual annotation. Analysis opens each figure
in its own window and exports PDF/SVG, tables and Python/R/MATLAB reproduction code.
Automatic result PNG previews are disabled. Omnipose previews and exports now use
the same native-resolution tiled calculation; see the Mac/Windows comparison guide
before comparing historical and newly processed masks.

## Documentation

| Start here | Purpose |
| --- | --- |
| [Documentation index](docs/README.md) | All current guides |
| [User manual](docs/BACTOMATE_USER_MANUAL.md) / [PDF](docs/BactoMate.pdf) | Complete workflow and control reference |
| [Testing guide — English](GUIDE_TEST_BACTOMATE_EN.md) / [French](GUIDE_TEST_BACTOMATE_FR.md) | Installation and acceptance checks |
| [Custom changes — English](MODIFICATIONS_BACTOMATE_EN.md) / [French](MODIFICATIONS_BACTOMATE_FR.md) | Consolidated changes since the upstream baseline |
| [Simple Analysis](docs/NEW_ANALYSIS.md) / [Figure guide](docs/FIGURE_GUIDE.md) | Conditions, replicates, demographs, maxima and kymographs |
| [Mac/Windows comparison](docs/MAC_WINDOWS_REPRODUCIBILITY.md) | Shared versions, CPU reference and corrected segmentation failures |
| [Release notes](docs/RELEASE_NOTES.md) | Custom development milestones and validation limits |

## Scientific interpretation and attribution

Cell area uses mask pixels and calibration; length and width are equivalent-ellipse
axes. Display LUTs never change the source fluorescence measurements. Segmentation
labels do not establish tracking identity or pole age. Replicate means are shown
explicitly; cell counts are not automatically biological replicates.

This work builds on [upstream BactoMate](https://github.com/Molinfect/BactoMate),
[Omnipose](https://omnipose.readthedocs.io/), [Cellpose](https://cellpose.readthedocs.io/)
and [Trackastra](https://github.com/weigertlab/trackastra). The figure workflow is
inspired by [MicrobeJ](https://pmc.ncbi.nlm.nih.gov/articles/PMC5010025/); it does not
run the Fiji plugin. See the upstream project for its citation and paper data,
and [docs/PAPER_DATA.md](docs/PAPER_DATA.md) for data access.

License: MIT; see [LICENSE](LICENSE).
