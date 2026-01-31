# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDFResolve is a bibliographic metadata extraction agent system that automatically extracts bibliographic information from PDF documents (scanned/OCR-required and text PDFs) and single images.

## Development Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run single test file
pytest tests/test_models.py

# Run with coverage
pytest --cov=pdfresolve

# Lint
ruff check src/

# Format
ruff format src/

# CLI usage
pdfresolve --help
pdfresolve info <file.pdf>
pdfresolve extract <file.pdf> -o output.json
```

## Project Structure

```
src/pdfresolve/
├── cli.py              # CLI entry point (typer)
├── core/
│   ├── config.py       # Configuration (Pydantic)
│   └── document.py     # Document class (PDF/image wrapper)
├── extraction/
│   └── page_selector.py  # Page selection strategies
├── parsing/            # Rule-based and LLM extraction (TODO)
├── validation/         # Field validation and scoring (TODO)
├── enrichment/         # Web search and expansion (TODO)
├── export/             # CSL-JSON, RIS, BibTeX output (TODO)
├── models/
│   ├── bibliography.py # BibliographyRecord, Author, DateParts
│   └── evidence.py     # Evidence, BoundingBox
└── utils/
    └── logging.py      # Logging setup
```

## Architecture

The system follows a multi-stage pipeline:

1. **Input**: PDF files or single images (cover/title pages)
2. **File Analysis**: Detect text layer presence → route to text or OCR pipeline
3. **Page Selection**:
   - OCR documents: p1, p2, last (conditionally p3, last-1, TOC)
   - Text PDFs: p1-p3, last
4. **Text Extraction**: Multi-language OCR (EN/FR/RU) or direct text extraction
5. **Document Classification**: Detect type via keywords (journal article, series/bulletin, book/report)
6. **Two-Phase Extraction**:
   - Phase 1: Rule-based extraction (regex for year, pages, volume, place)
   - Phase 2: LLM-based structured extraction (authors, title, container)
7. **Validation**: Confidence scoring, field conflict detection
8. **Agent Loop**: Automatic expansion search for missing fields (with iteration limits)
9. **Web Search**: Optional augmentation for incomplete data
10. **User Review UI**: Evidence display with approve/modify/retry actions
11. **Export**: CSL-JSON (primary), RIS, BibTeX

## Key Design Principles

- All extracted fields must include evidence (page number + source text/image capture)
- Confidence scoring drives routing: high → auto-confirm, low → web search/user review
- Agent loop must have iteration limits to prevent infinite loops
- Evidence collection is first-class throughout the pipeline
- OCR strategy: "fast and rough → precise only on failures"

## Data Models

- `BibliographyRecord`: CSL-JSON compatible record with status and evidence
- `Evidence`: Source tracking with page number, bbox, confidence
- `RecordStatus`: `confirmed`, `needs_review`, `failed`

## Output

- `data/records/` - CSL-JSON bibliographic records
- `data/evidence/` - Source captures and page images
