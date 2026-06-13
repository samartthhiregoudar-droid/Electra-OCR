from fastapi import FastAPI, UploadFile, File, HTTPException
from rapidfuzz import fuzz
from database import init_db, get_connection, search_voters_by_name_prefix
from ocr_engine import run_ocr
from parser import parse_voters
from pdf_text_extractor import extract_pdf_text_by_page
from pdf_renderer import get_pdf_page_count, render_pdf_page
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize DB on startup
@app.on_event("startup")
def on_startup():
    init_db()

# -------------------------------
# Root endpoint
# -------------------------------
@app.get("/")
def home():
    return {"message": "Electoral Roll Voter API Running"}

# -------------------------------
# Upload PDF and store voters
# -------------------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    
    try:
        with open(temp_path, "wb") as f:
            f.write(contents)

        all_lines = []
        text_pages = extract_pdf_text_by_page(temp_path)
        direct_text_pages_used = sum(1 for page_lines in text_pages if page_lines)
        ocr_pages_used = 0

        if direct_text_pages_used:
            logger.info("Using direct text extraction for %s page(s).", direct_text_pages_used)
            for page_number, page_lines in enumerate(text_pages, start=1):
                if page_lines:
                    all_lines.extend(page_lines)
                    continue

                all_lines.extend(run_ocr_for_page(temp_path, page_number))
                ocr_pages_used += 1
        else:
            logger.info("No usable selectable text found. Falling back to OCR for the full PDF.")
            page_count = len(text_pages) if text_pages else get_pdf_page_count(temp_path)
            for page_number in range(1, page_count + 1):
                all_lines.extend(run_ocr_for_page(temp_path, page_number))
                ocr_pages_used += 1

        voters = parse_voters(all_lines)
        if not voters:
            return {
                "message": "No voters found in the document.",
                "inserted_records": 0,
                "direct_text_pages_used": direct_text_pages_used,
                "ocr_pages_used": ocr_pages_used,
            }

        inserted_count = save_voters(voters)

        return {
            "inserted_records": inserted_count,
            "total_voters_parsed": len(voters),
            "direct_text_pages_used": direct_text_pages_used,
            "ocr_pages_used": ocr_pages_used,
        }
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def run_ocr_for_page(pdf_path, page_number):
    try:
        image = render_pdf_page(pdf_path, page_number, dpi=300)
    except Exception as e:
        logger.error(f"PDF rendering failed for page {page_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to render PDF page {page_number}: {str(e)}")

    try:
        return run_ocr(image)
    except Exception as e:
        logger.error(f"OCR failed for page {page_number}: {e}")
        return []


def save_voters(voters):
    conn = get_connection()
    cursor = conn.cursor()

    inserted_count = 0
    for voter in voters:
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO voters
            (voter_id, name, fathers_name, house_number, age, gender, photo_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                voter.get("voter_id"),
                voter.get("name"),
                voter.get("fathers_name"),
                voter.get("house_number"),
                voter.get("age"),
                voter.get("gender"),
                voter.get("photo_status")
            ))
            inserted_count += 1
        except Exception as e:
            logger.warning(f"Failed to insert voter {voter.get('voter_id')}: {e}")

    conn.commit()
    conn.close()
    return inserted_count

# -------------------------------
# Fetch by voter ID
# -------------------------------
@app.get("/person/{voter_id}")
def fetch_by_id(voter_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM voters WHERE voter_id=?", (voter_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Person not found")

    return {
        "voter_id": row[0],
        "name": row[1],
        "fathers_name": row[2],
        "house_number": row[3],
        "age": row[4],
        "gender": row[5],
        "photo_status": row[6]
    }

# -------------------------------
# Fetch by name (optimized fuzzy search)
# -------------------------------
@app.get("/person/by-name/{name}")
def fetch_by_name(name: str):
    # Step 1: Get a candidate pool using SQL prefix/contains search
    # We take the first 3 chars or the whole name if shorter
    prefix = name[:3]
    candidates = search_voters_by_name_prefix(prefix)
    
    if not candidates:
        # If no candidates found with prefix, it might be a middle-of-name match
        # or we might need to broaden the search, but for now we search all if prefix fails
        # or just return not found to be efficient.
        # Let's try one more broader search if prefix failed
        candidates = search_voters_by_name_prefix("")

    best_match = None
    best_score = 0
    query_name = name.strip().lower()

    for row in candidates:
        db_name = row[1]
        if not db_name:
            continue

        score = fuzz.token_sort_ratio(
            query_name,
            db_name.strip().lower()
        )

        if score > best_score:
            best_score = score
            best_match = row

    if best_match is None or best_score < 70: # Lowered threshold slightly for more results
        raise HTTPException(status_code=404, detail="Person not found with sufficient confidence")

    return {
        "voter_id": best_match[0],
        "name": best_match[1],
        "fathers_name": best_match[2],
        "house_number": best_match[3],
        "age": best_match[4],
        "gender": best_match[5],
        "photo_status": best_match[6],
        "match_confidence": best_score
    }
