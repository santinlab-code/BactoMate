# Install and launch the custom branch on Windows

Current branch: **BactoMate_Custom_New-Analyses**. Reviewed 1 November 2026.
[Setup overview](../setup/README.md) · [Acceptance tests](../GUIDE_TEST_BACTOMATE_EN.md)

## Install from this branch

An upstream `BactoMate-win64.zip` release may not contain the custom functions.
Use this branch's source ZIP/clone, or a portable build explicitly produced from
it. The automatic GitHub source archive is code, not a bundled Python application.

Requirements: Windows 10/11 x64, plain **Python 3.11 x64** from python.org with
its `py` launcher, and the [Microsoft VC++ Redistributable x64](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
Use a writable folder such as `C:\Users\<you>\BactoMate_custom`; avoid Program
Files and do not run as Administrator, which can interfere with drag-and-drop.
Conda/Store interpreters and other Python versions are not installer substitutes.

Clone/extract the entire active branch. In Command Prompt at the folder containing
`main.py`, run:

```bat
setup\windows\install.bat
launch_windows.bat
```

If Windows blocks scripts, unblock the downloaded ZIP in Properties and extract
again. Run the installer from an existing Command Prompt to retain failure output.
The installer verifies Python, creates `venv`, installs constrained requirements
and the editable package, applies patches/Spotiflow repairs, checks the result
and creates launcher assets. A prebuilt dbscan wheel avoids the normal need for
C++ Build Tools. Internet access is needed for packages/models not yet installed.

## Verify and start later

```bat
venv\Scripts\python.exe main.py --version
venv\Scripts\python.exe main.py --smoke-test
launch_windows.bat
```

Alternatively activate `venv\Scripts\activate` and run `bactomate`. The version
can remain 2.9.5; use the Git commit/branch to identify the custom build. Keep the
project in its final location. Recreate its venv after a move or new ZIP extraction;
a copied venv can still point to the old code.

## Troubleshooting

| Symptom | Check or repair |
| --- | --- |
| No installer window / immediate close | Run from Command Prompt, confirm extracted source root and Python 3.11 x64 |
| DLL load failed / c10.dll / torch import failure | Install VC++ x64 runtime; confirm 64-bit Python; rebuild with the installer |
| dbscan wheel/build error | Use platform installer/constraints with Python 3.11 x64 rather than compiling an unpinned version |
| Drag-and-drop fails | Run normally, without Administrator privileges |
| CUDA unavailable | Check NVIDIA driver/device and installed PyTorch build; CPU remains supported |
| ILP tracking import failure | Reinstall constrained requirements in this venv; the solver API must match Trackastra |

For incompatible Cellpose/Omnipose checkpoint loading:

```bat
venv\Scripts\python.exe setup\apply_all_patches.py
venv\Scripts\python.exe main.py --smoke-test
```

For `cannot import name 'unique_nonzero' from 'ncolor'`, Omnipose expects the 1.x
API; installing Cellpose again is not the remedy:

```bat
venv\Scripts\python.exe -m pip install "ncolor>=1.4.3,<2"
```

For Spotiflow `wandb.proto` errors or TensorFlow protobuf/tensorboard conflicts:

```bat
venv\Scripts\python.exe setup\windows\ensure_spotiflow_deps.py
venv\Scripts\python.exe main.py --smoke-test
```

The maintained constraints use a TensorFlow-safe dependency range. Avoid a blanket
upgrade to latest wandb/protobuf. If required, the existing repair range is:

```bat
venv\Scripts\python.exe -m pip install "wandb>=0.22.0,!=0.23.1,<0.28.0" "protobuf>=4.25.0,<5.0.0" "tensorboard>=2.12.0,<2.17.0"
```

Inspect `Logs` in the project; a non-writable project can fall back to
`%APPDATA%\BactoMate\Logs`. Preserve the relevant install/GUI log and exact steps.

## Manual recovery

Prefer the installer, which also handles platform-specific steps. In an explicitly
created Python 3.11 x64 environment, the core fallback is:

```bat
py -3.11 -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt -c setup\windows\constraints.txt
venv\Scripts\python.exe -m pip install -e .
venv\Scripts\python.exe setup\apply_all_patches.py
venv\Scripts\python.exe setup\windows\ensure_spotiflow_deps.py
venv\Scripts\python.exe main.py --smoke-test
venv\Scripts\python.exe main.py
```

Do not create over an environment you need to preserve. For source updates use
a clean Git pull on the active branch or a new ZIP folder and its new venv.

## Custom portable bundles

Maintainers can build a Windows portable folder/ZIP from this branch on Windows;
see [packaging](../build/README.md). A delivered portable build includes its own
runtime. Extract the whole folder and launch its `BactoMate.bat`, keeping the
contents together. Do not run the source installer inside a portable distribution.
Test that its recorded commit matches the intended custom revision; a generic
upstream release filename is not evidence of that match.
