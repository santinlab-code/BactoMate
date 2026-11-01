# Install and launch BactoMate Custom

Use **BactoMate_Custom_New-Analyses** from
[santinlab-code/BactoMate](https://github.com/santinlab-code/BactoMate/tree/BactoMate_Custom_New-Analyses).
Reviewed 1 November 2026. The earlier V1/Analyses branches are removed. Upstream
release apps may not contain this custom code; install this branch's source or a
bundle explicitly built from it.

## Choose the folder and interpreter

Install plain **Python 3.11**, with 64-bit Python on Windows. The platform installers
verify the interpreter; avoid substituting Conda, Store Python or an arbitrary
newer Python. GPU is optional. Keep source in a user-writable folder such as
`~/BactoMate_custom` or `C:\Users\<you>\BactoMate_custom`.

Clone the active branch or extract its complete ZIP; the project root contains
`main.py`, `requirements.txt` and the launchers. Create the venv in its final
location. Copying/moving a venv or renaming its parent can break absolute shebangs
and editable-package paths. Recreate it when moving/replacing the project.

## macOS

In Terminal at the project root:

```bash
chmod +x setup/macos/*.sh launch_gui.sh
./setup/macos/install.sh
./launch_gui.sh
```

The installer delegates to setup_fresh_env.sh, logs to `Logs/install.log`, creates
a fresh `venv`, installs dependencies/editable package, applies backend patches
and checks the result. An existing venv is kept as `venv.previous` until the smoke
check succeeds. Follow the installer's recovery message if a step fails.

For later launches, if installed directly under your home folder:

```bash
cd ~/BactoMate_custom
./launch_gui.sh
```

If the Qt cocoa plugin is broken:

```bash
./setup/macos/repair_pyqt6.sh
```

For a clean environment rebuild, rerun `./setup/macos/install.sh`. Model/device
problems are separate from GUI launch failures; check the application log.

## Windows

Install the [VC++ Redistributable x64](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist),
use Python 3.11 x64 and open Command Prompt at the project root:

```bat
setup\windows\install.bat
launch_windows.bat
```

Do not use Program Files or run as Administrator. The installer creates a venv,
installs constrained dependencies/wheels, applies patches and creates launch
assets. See [the Windows guide](../docs/INSTALL_AND_LAUNCH_windows.md) for DLL,
Spotiflow, ncolor, solver and CUDA repairs. Legacy root/setup installer stubs
forward to the platform scripts; use the paths above for new instructions.

## Verify and update

Activate this project's environment before diagnostic/CLI commands:

```bash
source venv/bin/activate
python main.py --version
python main.py --smoke-test
```

Windows equivalents are `venv\Scripts\activate` or direct
`venv\Scripts\python.exe main.py --smoke-test`. Version 2.9.5 is the upstream
package version; record `git rev-parse HEAD` to identify custom code.

With a clean checkout already on the active branch:

```bash
git status
git pull --ff-only
```

Preserve local edits before updating. If dependencies change, reinstall with the
platform installer. For a source ZIP update, extract a fresh folder and build its
venv there; keep experiment results separate from source replacement.

Manual fallback for a suitable existing Python 3.11 environment:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python setup/apply_all_patches.py
python main.py --smoke-test
```

On Windows, prefer the installer because it also applies platform constraints and
repairs. Do not upgrade scientific/backend dependencies indiscriminately.

## Helper map

| Location | Role |
| --- | --- |
| `setup/macos/` | Installer, real launcher, fresh venv, Qt repair and GPU helpers |
| `setup/windows/` | Installer, launcher templates, constraints and dependency repairs |
| `setup/apply_all_patches.py` | Shared Omnipose/Cellpose compatibility patches |
| `setup/dev/` | Optional developer diagnostics |
| `build/` | Native app/bundle packaging; not required for source launch |

After installation follow [the acceptance guide](../GUIDE_TEST_BACTOMATE_EN.md).
The [user manual](../docs/BACTOMATE_USER_MANUAL.md) covers the complete workflow.
