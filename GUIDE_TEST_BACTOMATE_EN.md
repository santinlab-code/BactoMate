# Testing the BactoMate development version

## Which version should I install?

The `test/bactomate-optimisations` branch contains the current code and the
changes described in `MODIFICATIONS_BACTOMATE_EN.md`. It is source code with
installation scripts, not a pre-built Windows or macOS application. Applications
from the official release do not contain these changes.

Download the branch as a ZIP and extract it into a new folder, such as
`BactoMate-test` in Documents. Do not replace your regular installation. The
archive does not contain the reference ND2 file or the test results generated here.

## Windows

Project requirements: 64-bit Windows 10/11, 64-bit Python **3.11** from
python.org (avoid Conda and Microsoft Store Python), and the 64-bit Microsoft
Visual C++ Redistributable. When installing Python, select the option to add it
to PATH.

1. Fully extract the archive into Documents.
2. Open the extracted folder containing `main.py` and `requirements.txt`.
3. Double-click `install_windows.bat` and let the installation finish.
4. Double-click `launch_windows.bat` to start this version.

If Windows blocks the downloaded archive, open its Properties and use Unblock,
if that option is shown, then extract it again. The detailed project guide is
`docs/INSTALL_AND_LAUNCH_windows.md`.

## macOS

Project requirements: macOS 10.15 or later and Python **3.11**. Installing from
source requires a few Terminal commands. Open Terminal (Applications → Utilities).
Type `cd` followed by a space, drag the extracted folder containing `main.py`
into the Terminal window, and press Return. Then run these two lines one at a time:

```bash
chmod +x setup/macos/*.sh launch_gui.sh
./setup/macos/install.sh
```

The installer downloads the required libraries; the first installation may take
several minutes. If an error occurs, share the displayed message before trying to
change Python. This archive was verified in our Linux environment; installation
and interface behavior on your Mac still need to be confirmed by this test.

To launch BactoMate later, run this from the same folder:

```bash
./launch_gui.sh
```

## Linux

The cloud test environment runs Linux with Python 3.11. The project's user-facing
procedures mainly cover Windows and macOS. For a local Linux installation, specify
the distribution so that the graphical dependencies and installation can be adapted.

## Test workflow using the reference file

Use a copy of the ND2 file and a new results folder for these tests.

### A. Conversion

1. Select the ND2 file in File Conversion.
2. Assign the Phase role to the PH3 channel.
3. Select both Fluorescence and Foci for GFP and mCherry.
4. Convert all three positions and all three channels.
5. Confirm that nine TIFF files are produced, containing XY001, XY002, and XY003.

### B. Segmentation

1. Segment the phase images with the model normally used by the team.
2. Open the preview and confirm that the outlines leave the cells visible.
3. Change the color with Outline color… and check the result.

### C. Filtering and curation

The image opens separately: move it to a second screen if desired. Choose Cells
or Foci in that window, click an object, and check the yellow box and selected
table row. Press Delete or Backspace to exclude it, then restore it with Keep
selected objects. Closing the image window reattaches it; Detach image detaches
it again.

1. Open Preview filters and the Cell table / Manual selection / History panel.
2. Record the initial cell count, then apply an area filter.
3. Check the new count and the criteria recorded in the history.
4. Select a cell in the table and use Exclude selected objects.
5. Add it back with Keep selected objects.
6. Use Use filters for selected objects to return to the automatic decision.
7. Export with Filter File/Folder and inspect the filtered mask.

### D. Independent channel settings and reusable parameters

1. Under View, select GFP and enter a recognizable filtering threshold.
2. Switch to mCherry and enter a different threshold.
3. Return to GFP and confirm that its value and checkboxes were retained.
4. Export and locate the cell JSON and the two foci JSON files.
5. Change the GFP settings, then import only the GFP JSON file.
6. Confirm that GFP is restored without changing mCherry or the cell settings.

Foci selection tests require the CSV files produced by foci detection. If foci
have not yet been detected, run detection before this test.

### E. Colocalization preview

1. Under Analyze → Foci analysis, confirm Max distance = 3 px and Threshold =
   2 px, unless a saved session has loaded other values.
2. Open Preview distances… and click a cell.
3. Select GFP and mCherry for A and B, then choose the phase or fluorescence background.
4. Check the grid and the 1 px marker in the zoomed view.
5. On a cell containing detected foci, change both distances and observe the displayed
   circles and pairs.
6. Confirm that the Foci analysis values follow changes made in the preview.

## Reporting a problem

State which section you used, what you did, what you expected, and what happened.
Include the file name, XY position, channel, and frame concerned, as well as the
exact error message or a screenshot. If installation fails, share `Logs/install.log`
on macOS or `Logs/install_last.log` on Windows, if that file was created.

The window may still display the base version number **2.9.5**, because no new
official release number has been assigned. The Preview distances… button and the
Filtering import/export buttons identify this test version.
