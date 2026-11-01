# Package BactoMate Custom

Maintainer guide for **BactoMate_Custom_New-Analyses**, reviewed 1 November 2026.
End users can [install from source](../setup/README.md); no build step is needed.
A generic upstream release app may not contain this branch's custom features.

## Build the intended code

Check the branch and commit, keep a clean source tree and install the platform
requirements first. Do not use the removed V1/Analyses branches or merge this
work to another branch as a prerequisite. The inherited package version remains
2.9.5, so record the custom commit in the distributed build's accompanying notes.
Do not publish a release/tag or upload experiment data merely to create a local
build. Packaging is separate from updating this branch's source/docs on GitHub.

## Native outputs

| Platform | Commands from the project root | Output |
| --- | --- | --- |
| macOS | `./build/macos/build_app_bundle.sh`, then `./build/macos/create_dmg.sh` | dist/BactoMate.app and dist/BactoMate.dmg |
| Windows | `build\windows\build_windows_bundle.bat`, then `build\windows\create_windows_zip.bat` | dist\BactoMate\ and dist\BactoMate-win64.zip |

Run these on their target operating system after its setup installer. The macOS
scripts build the native launcher/icons and app payload. The Windows scripts
include a Python runtime and portable launcher. Keep all files of a portable
folder together. Inspect build logs and test on a clean target machine; building
successfully on the developer computer is not portability proof.

Inherited public-packaging rules omit developer/internal artifacts and provide an
empty Logs directory. Check the actual packaged manifest before distributing;
never include local microscopy experiments, tokens, work folders or an unintended
old venv. The repository's optional upstream release workflows do not guarantee
that this custom branch is built or uploaded automatically.

## Distribution checks

Launch, quit and reopen the packaged app. Check the recorded commit, smoke test,
conversion, a small segmentation/filtering run and automatic Analysis handoff.
On macOS, test focus/close dialogs on native windows; on Windows, test paths with
spaces and runtime imports. Use the [acceptance guide](../GUIDE_TEST_BACTOMATE_EN.md).

Unsigned/ad-hoc-signed macOS builds can require the normal Finder Open / Privacy &
Security approval for apps from outside the App Store. Follow the build's supplied
launcher instructions; managed computers may require administrator/IT policy
support. Do not assume another build's upstream DMG resolves custom-code issues.

## Documentation PDF

The current manual is docs/BACTOMATE_USER_MANUAL.md, with PDF at docs/BactoMate.pdf.
To rebuild from the docs directory with Pandoc, XeLaTeX and DejaVu Sans installed:

```bash
cd docs
pandoc BACTOMATE_USER_MANUAL.md -o BactoMate.pdf \
  --pdf-engine=xelatex --toc -V mainfont="DejaVu Sans" \
  -V monofont="DejaVu Sans Mono" -V geometry:margin=20mm \
  -V fontsize=10pt -V colorlinks=true
```

Build after editing the source and inspect page breaks, tables, links and text
extraction. This manual PDF is separate from the legacy marketing brochure
created by bactomate.scripts.generate_bactomate_pdf. Documentation screenshots
under docs/images are illustrative assets, not automatic pipeline PNG output.
