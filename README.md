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
