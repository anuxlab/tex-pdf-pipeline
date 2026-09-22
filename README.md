# TeX PDF Pipeline — End-to-End Test Fixtures

These files are designed to be copied into the root of `anuxlab/tex-pdf-pipeline`.

## Normal end-to-end test

1. Copy the contents of this directory into the repository root.
2. Run locally:

   ```bash
   make pdf
   ```

   or:

   ```bash
   latexmk -pdf main.tex
   ```

3. Push the changes to `main` or manually run the GitHub Actions workflow.
4. Expected output: `main.pdf`, with bibliography, resolved cross-references,
   a table, equations, and a TikZ-generated figure.

## What this fixture exercises

- `main.tex` as the configured master (`ci/pipeline.yaml` -> `report`)
- `pdflatex` + `latexmk`
- BibLaTeX + Biber
- Multiple `\input` chapter files
- Relative paths with `work_in_root_file_dir: true`
- Cross-references and labels
- Mathematics
- Tables
- TikZ graphics
- PDF artifact generation

## Negative test

`tests/broken.tex` is intentionally malformed. It is **not** referenced by the
normal `books` matrix. Use it only when testing that preflight/diagnostics and
failure handling work as expected.
