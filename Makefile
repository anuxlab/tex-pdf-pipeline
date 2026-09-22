MASTER  ?= main.tex
CONFIG  ?= ci/pipeline.yaml
BOOK    ?= report

.PHONY: all pdf config pkgs verify-pkgs preflight clean distclean

all: pdf

pdf:
	latexmk -pdf $(MASTER)

config:
	@python3 .github/scripts/book_ci.py config --file $(CONFIG) --out /dev/stdout

pkgs:
	@python3 .github/scripts/book_ci.py packages --file $(CONFIG) --book $(BOOK) --out /dev/stdout

verify-pkgs:
	@python3 .github/scripts/book_ci.py verify-packages --file $(CONFIG) --book $(BOOK)

preflight:
	python3 .github/scripts/book_ci.py preflight --master $(MASTER)

clean:
	latexmk -c $(MASTER)

distclean:
	latexmk -C $(MASTER)
	rm -f *.bbl *.bcf *.run.xml