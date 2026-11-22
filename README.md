# Reading Brain

A personal knowledge-search tool that turns years of e-book highlights into a searchable, offline "second brain."

It parses highlights exported from **WeRead** (via the Obsidian WeRead plugin), builds keyword and semantic search indexes plus a book-similarity graph, and packages everything into a single self-contained HTML search app.

> The author's own library has 300 books and 5,400+ highlights. That data is private and is **not** included here. The repo ships with a small sample vault of public-domain quotes (Thoreau, Marcus Aurelius) so anyone can run the full pipeline.

<!-- Add a screenshot of the search app here, e.g. ![screenshot](docs/screenshot.png) -->

## Features

- **Evidence-first parser.** Reads Markdown in read-only mode and never summarizes or rewrites the text. Every highlight keeps its book, chapter, timestamp, and source line range. Malformed blocks become warnings in an audit report instead of being silently dropped.
- **Hybrid search** that combines character-level TF-IDF (works for Chinese without a word tokenizer) with LSA (TruncatedSVD), which finds related highlights even when the wording differs.
- **Book-similarity graph** that links books by the cosine similarity of their highlights.
- **One-file search app.** A Python build step injects the data into an HTML template, so the result runs offline in any browser.
- **One-command refresh.** `update.sh` runs the whole pipeline: parse → index → graph → app → change report.

## Pipeline

```
Obsidian vault (WeRead Markdown)
   │  reading_brain/  (parser + audit, stdlib only)
   ▼
output/entries.jsonl, books.jsonl, audit.json
   │  build_index.py   TF-IDF + LSA index
   │  build_graph.py   book-similarity graph
   │  build_app.py     inject data into app_template.html
   ▼
阅读大脑检索台.html   (self-contained search app)
```

## Quick start (sample data)

```bash
pip install -r requirements.txt

# 1. Parse the sample vault
python3 -m reading_brain.cli --source examples/sample_vault --output output

# 2. Build the search index and graph
python3 reading-brain/scripts/build_index.py
python3 reading-brain/scripts/build_graph.py

# 3. Search from the command line
python3 reading-brain/scripts/query.py "solitude" --top 3

# 4. Build the browser app
python3 reading-brain/scripts/build_app.py
```

A prebuilt demo from the sample data is in `examples/demo.html`.

To run it on your own library, point `update.sh` at your vault:

```bash
READING_BRAIN_SOURCE="$HOME/path/to/Obsidian Vault" ./reading-brain/scripts/update.sh
```

## Tech stack

Python 3.10+ (standard library for parsing; scikit-learn, SciPy, and NumPy for indexing), plus vanilla JavaScript and HTML for the search app.

## Project structure

```
reading_brain/            parser, frontmatter reader, data models, audit, CLI
reading-brain/scripts/    index / graph / app builders, query CLI, update.sh
examples/sample_vault/    public-domain sample highlights in WeRead format
examples/demo.html        app built from the sample data
```

## Limitations

The semantic search is statistical (LSA), not neural. It can be pulled off-topic by very frequent characters. A planned upgrade is to swap in a sentence-embedding model such as `BAAI/bge-small-zh-v1.5`.

## Author

PeiJin Zhao, UMass Amherst
