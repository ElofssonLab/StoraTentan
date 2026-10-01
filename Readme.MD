# Stora Tentan (oral exam in bioinformatics)

This book ( written using quarto) is an attempt to provide more
detailed reading material for the oral exam for PhD students in
bioinformatics at DBB, Stockholm University.


## Current instructions

IN data/Stora\ Tentan\ Bioinfo\ 2025.md 


## Old material

The other documents in data/* are old instructions. They basically cover the same material (except never things) but in a more detailed form


## Instructions to Claude/Codex:

Set up a system using Quarto (qmd) to write a good set of reading
instructions for the oral exam in bioinformatics. You should base it
on the current rules in in the file above, but also on the information
from earlier descriptions. I would organise it as follows:;

- A set of topics (see current instructions)
-- A short introduction about htis topic (taken from open access material)
-- Based on up to date material (wikipedia, free open access review papers etc) write a 
-- A list of key papers to read. Preferable reviews
-- A list of good lectures online that discusses the topics

Can you start with setting up the papers and the list of papers (mainly from thte material in data/* but also from your knowledge.


## Building the book

    quarto preview      # live preview while editing
    quarto render       # builds HTML and PDF into _book/
                        # (_book/Stora-Tentan-in-Bioinformatics.pdf)

Render the whole project, not `quarto render index.qmd`: a single file
does not pick up the book structure. Rendering only one format
(`--to pdf`) clears the other format from `_book/`.

## Layout

- `_quarto.yml` – book configuration and chapter order
- `index.qmd` – about the exam (from the 2025 instructions)
- `chapters/NN-*.qmd` – one chapter per exam topic: introduction, key concepts,
  background reading, key papers (★ = mandatory in old lists), online lectures
- `chapters/textbooks.qmd` – appendix with textbooks and general resources
- `preamble.tex` – LaTeX settings for the PDF (★ glyph, URL breaking)
- `styles.css` – shows per-chapter reference lists in HTML
- `references.bib` – **generated**, do not edit by hand (see below)

## Adding papers

1. Add a line `key<TAB>doi` to `scripts/papers.tsv` (or a full BibTeX entry
   to `scripts/manual.bib` for items without a DOI).
2. Run `python3 scripts/fetch_bib.py`. It fetches BibTeX from Crossref
   (cached in `scripts/.bibcache/`), prints `key, first author, year, title`
   so you can check the DOI points to the right paper, and rewrites
   `references.bib`. Fixes for bad Crossref metadata go in `AUTHORS`/`EXTRA`
   in the script.
3. Cite it in a chapter as `- @key — one-line comment`.
