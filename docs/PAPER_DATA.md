# Upstream paper data and attribution

This custom software branch is **BactoMate_Custom_New-Analyses** in
[santinlab-code/BactoMate](https://github.com/santinlab-code/BactoMate/tree/BactoMate_Custom_New-Analyses).
Its private/local test images are not automatically public research data. The
custom V1/Analyses branches were removed; this page does not ask users to recreate
them. Reviewed 1 November 2026.

## Upstream BactoMate resources

The upstream project provides its publication/citation and tutorials at
[Molinfect/BactoMate](https://github.com/Molinfect/BactoMate). The inherited paper
reference is Hallenga et al. (2026), *BactoMate: an integrated platform for
reproducible bacterial microscopy analysis*;
[preprint](https://www.biorxiv.org/content/10.64898/2026.08.06.743177v1).
Use the current upstream citation metadata when preparing a manuscript, and record
the custom branch/commit plus analysis parameters for work using this fork.

The upstream raw-data branch is separate from this fork's custom development:

- [Browse upstream paper-data](https://github.com/Molinfect/BactoMate/tree/paper-data)
- [Download upstream data ZIP](https://github.com/Molinfect/BactoMate/archive/refs/heads/paper-data.zip)

```bash
git clone --branch paper-data --depth 1 \
  https://github.com/Molinfect/BactoMate.git BactoMate-paper-data
```

These links describe the upstream publication resources, not an assurance that
the upstream service/files were revalidated during this documentation update.
They do not contain the user's full laboratory dataset or validate the custom
foci/colocalization results.

## Store and share your own results

Keep raw images, calibration, original masks, curation sidecars, filtered outputs,
analysis workbooks, group assignments and figure bundles with the experiment.
A figure bundle includes selected data/code but is not the entire raw experiment.
Keep large microscopy data outside the software source checkout where possible.
Adding .gitignore later does not remove files already committed to Git history.

For a publication dataset, use an appropriate archive such as Zenodo, Figshare or
an institutional repository and link its DOI. Publish only data you intend to
share. A software source push is not a raw-data deposition. See
[Analysis exports](ANALYSIS.md#export-bundle) for figure-level provenance.
