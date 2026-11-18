# ElectraOCR: High-Throughput Electoral Roll Information Extraction System

A small FastAPI project that extracts voter records from electoral roll PDFs, stores them in SQLite, and lets you search by voter ID or fuzzy name match.

This is a learning/demo project, not a production-grade voter database and this is only for a type of particular dataset. But the core OCR engine can be used for other generic purposes.

## Features

- Upload an electoral roll PDF.
- Try direct selectable-text extraction first with `pypdf`.
- Fall back to PyMuPDF page rendering plus PaddleOCR only for pages without usable selectable text.
- Parse voter ID, name, relation name, house number, age, gender, and photo status.
- Store parsed records in SQLite.
- Search records by voter ID or approximate name.
- Evaluate parser accuracy with repeatable metrics.

## Project Structure

```text
.
|-- main.py                  # FastAPI routes
|-- parser.py                # Text line parser
|-- pdf_text_extractor.py    # Selectable PDF text extraction
|-- pdf_renderer.py          # PDF page rendering for OCR fallback
|-- ocr_engine.py            # PaddleOCR wrapper
|-- database.py              
|-- test_app.py              # Basic parser/database tests
|-- scripts/
|   `-- evaluate_parser.py   # Accuracy metrics for parser fixtures
|-- data/
|   `-- evaluation_cases.json
|-- uploads/                 
|-- requirements.txt
|-- .env.example
`-- .gitignore
```

## Extraction Strategy

The upload endpoint uses a hybrid path:

1. Try `pypdf` text extraction on each page.
2. If a page has enough selectable text, parse that text directly.
3. If a page has no usable selectable text, render only that page to an image with PyMuPDF and run PaddleOCR.

This is faster and usually more accurate than always running OCR. OCR is still needed for scanned PDFs because scanned pages do not contain selectable text.

The upload response includes:

- `direct_text_pages_used`
- `ocr_pages_used`

These counts show which extraction method was used.

## Setup

Use Python 3.10 if possible. PaddleOCR/PaddlePaddle can be sensitive to Python and platform versions.

```powershell
python -m venv venv310
.\venv310\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy the example environment file:

```powershell
copy .env.example .env
```

`POPPLER_PATH` is not required. OCR fallback uses PyMuPDF for page rendering.

## Run the API

```powershell
uvicorn main:app --reload
```

Open:

- API: <http://127.0.0.1:8000>
- Docs: <http://127.0.0.1:8000/docs>

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Health check |
| `POST` | `/upload` | Upload a PDF and insert parsed voters |
| `GET` | `/person/{voter_id}` | Fetch one voter by ID |
| `GET` | `/person/by-name/{name}` | Fuzzy search by name |

## Test Parser and Database

```powershell
python test_app.py
```

## Measure Parser Accuracy

The evaluation script compares parser output against labeled OCR/text-line fixtures in `data/evaluation_cases.json`.

```powershell
python scripts/evaluate_parser.py
```

Metrics reported:

- `record_precision`: how many predicted voter IDs were correct.
- `record_recall`: how many expected voter IDs were found.
- `record_f1`: balanced score for record detection.
- `exact_record_accuracy`: percentage of expected records where every field matched.
- `field_accuracy`: field-level accuracy across found records.

Add more real samples to `data/evaluation_cases.json` to get a more honest score. The current fixtures are small smoke tests, so they prove parser behavior but do not prove real-world accuracy.

## Prepare for GitHub

This repo ignores local secrets, virtual environments, SQLite databases, generated logs, and uploaded PDFs. Before pushing, create a repository and run:

```powershell
git init
git add .
git commit -m "Prepare electoral text extraction API"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

Do not commit `.env`, `voters.db`, `venv310`, or private electoral roll PDFs.
