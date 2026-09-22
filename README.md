# tex-pdf-pipeline
To Build a CI/CD pipeline to automate the compilation of your LaTeX documents

Handling Multiple .tex Files and Compilation Order

# The root_file input in the latex-action is the key to managing multiple documents:
- Specifying Files: You can provide a multi-line list of files. Each entry is treated as a bash glob pattern, so you can even use wildcards like **/*.tex if you want to compile every document in your project.
- Controlling Order: The documents are compiled in the exact order you list them in the root_file block. This is useful if you have documents that depend on the output of a previous one.
- Working Directory: Setting work_in_root_file_dir: true is highly recommended for multi-document projects. It tells the action to change into the directory of each root file before compiling, which helps latexmk correctly find relative paths for images, bibliographies, and included chapters.

#Uploading PDFs and Logs

The actions/upload-artifact@v4 step is used to make the compiled PDFs and any log files available for download after the workflow runs.
- name: A descriptive name for the artifact bundle (e.g., compiled-pdfs).
- path: A newline-separated list of file paths to include. You can use wildcards like **/*.pdf to grab all PDFs from your repository.
- if-no-files-found: Set to warn to prevent the step from failing if no PDFs are found (e.g., if all compilations failed).

 # Advanced Tips

For more complex projects, you can use a .latexmkrc file in your repository root to define the compilation sequence for latexmk (which is the default compiler used by the action). This allows you to script the order of operations for projects with intricate dependencies, such as those using biber for bibliographies.

This setup provides a solid foundation for your LaTeX CI/CD pipeline. You can modify the list of files, add steps for specific tools, and customize the artifact names to fit your project's needs.

SOP — LaTeX Book CI/CD Pipeline

Purpose. A reproducible, error-loud pipeline that turns a multi-chapter LaTeX book — with per-chapter bibliographies, figures and a single-sourced "facts" layer — into a PDF on every push, and that surfaces every LaTeX/BibTeX error as a GitHub annotation plus a downloadable log bundle.

book/
├─ main.tex                     # master document — only \input, no prose
├─ preamble.tex                 # packages, macros, \addbibresource list
├─ .latexmkrc                   # local + CI build recipe
├─ Makefile                     # local mirror of the CI recipe
├─ chapters/
│   ├─ 00_frontmatter.tex
│   ├─ 01_intro.tex
│   ├─ 02_data.tex
│   │   …
│   └─ A_appendices.tex
├─ refs/                        # ONE .bib per chapter
│   ├─ 01_intro.bib
│   ├─ 02_data.bib
│   └─ …
├─ figures/
│   ├─ ch01/  fig-architecture.pdf …
│   ├─ ch02/  fig-lob.pdf …
│   └─ …
├─ facts/
│   ├─ facts.tex                # \newcommand for every number quoted
│   └─ SOURCES.md               # provenance for every fact ID
└─ .github/
    ├─ workflows/build-book.yml
    └─ scripts/book_ci.py


Rules that make the pipeline work:
Rule -> Why
main.tex contains only \input/\include, \bibliography, and \begin{document}…\end{document}	 -> one canonical entry point for latexmk

each chapter = exactly one chapters/NN_name.tex	-> 1:1 with its .bib and its figures/chNN/

every figure lives in figures/ch<NN>/ and is referenced with a root-relative path -> no \graphicspath ambiguity

every number/claim quoted in prose is a macro in facts/facts.tex -> facts change in one place; facts/SOURCES.md is the audit trail

no build artefacts committed (.gitignore covers *.aux *.log *.bbl *.bcf *.run.xml *.fls *.fdb_latexmk main.pdf)	-> CI is the source of truth

latexmk drives this automatically. It reads main.aux/main.bcf, notices a bibliography is needed, runs biber (or bibtex), and re-runs pdflatex until cross-references stabilise ($max_repeat = 5 in .latexmkrc).

Both bibliography backends are supported. The workflow does not care which you use:

    Standard (recommended): biblatex + biber — accepts many \addbibresource, supports per-chapter refsection reference lists.

    Legacy: natbib + bibtex — list all files in one \bibliography{refs/01_intro,refs/02_data,…}.

# Create the directories: mkdir -p ci .github/workflows .github/scripts

# Copy the six files above into their exact paths.

# Commit and push to main.

# Trigger the first run: push a trivial .tex edit, or go to Actions → Build book → Run workflow.

# Verify by checking the run page:

    - config job prints the JSON matrix and scalar outputs (this is your contract).

    - build job installs, verifies, preflights, compiles, diagnoses, uploads.

    - Artefacts report-pdf and report-logs appear on the run page — download them.

# To release: git tag v1.0 && git push origin v1.0 — the release job attaches report.pdf to a GitHub Release.

# To change build behaviour: edit ci/pipeline.yaml only. Never touch the workflow to change an engine, timeout, retention, or package list.

# Local sanity check before pushing

pip install pyyaml
make config       # shows exactly what CI will do
make verify-pkgs  # confirms your local TeX Live has every declared package
make pdf          # compiles the same way CI will

