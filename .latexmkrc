$pdf_mode     = 1;                       # pdflatex
$bibtex_use   = 2;                       # run biber/bibtex as needed
$max_repeat   = 5;                       # passes until refs stabilise
$pdflatex     = 'pdflatex -file-line-error -interaction=nonstopmode -synctex=1 %O %S';
$clean_ext    = 'bbl bcf run.xml fls fdb_latexmk synctex.gz';