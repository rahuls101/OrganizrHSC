import os
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
from datetime import datetime
from subject_config import name_to_code

# -----------------------------
# Individual extractors
# -----------------------------

def extract_subject_code(pdf):
    # Extracts the subject code from the PDF text
    text = pdf.get_text().lower()

    # Check for maths or english subjects first
    if "math" or "english" in text:
        # Check for maths levels
        if "mathematics extension 2" in text:
            return "MEX2"
        elif "mathematics extension 1" in text:
            return "MEX1"
        elif "mathematics advanced" in text:
            return "MADV"
        elif "mathematics standard" in text:
            return "MSTD"

        # Check for english levels
        elif "english extension 2" in text:
            return "EEX2"
        elif "english extension 1" in text:
            return "EEX1"
        elif "english advanced" in text:
            return "EADV"
        elif "english standard" in text:
            return "ESTD"

    # If not a maths or english subject, match by name from config
    for name, code in name_to_code.items():
        if name.lower() in text:
            return code
    return False

def extract_due_date(pdf):
    # Extracts the due date from the PDF text
    text_instances = pdf.search_for('Due Date')
    for inst in text_instances:
        rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)
        raw = pdf.get_text("text", clip=rect).strip()
        try:
            # Parse date string in expected format
            return datetime.strptime(raw, "%A, %d %B %Y")
        except ValueError:
            return False
    return False

def extract_title(pdf):
    # Extracts the task title from the PDF text
    text_instances = pdf.search_for('Task title')
    for inst in text_instances:
        extended_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)
        title = pdf.get_text("text", clip=extended_rect).strip()
        return title if title else False
    return False

def extract_description(pdf):
    # Placeholder for extracting description from PDF
    return 'Placeholder description'

def extract_weighting(pdf):
    # Extracts the weighting value from the PDF text
    text_instances = pdf.search_for('Weighting')
    for inst in text_instances:
        extended_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)
        weighting = pdf.get_text("text", clip=extended_rect).strip()

        weighting = str(weighting)
        weighting = int(weighting.replace('%', ''))

        return weighting if weighting else False

    return False

# -----------------------------
# Main processor
# -----------------------------

def process_file(file, upload_folder):
    # Handles the main PDF processing workflow

    # Save the uploaded file securely
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Open the PDF and extract information from the first page
    doc = fitz.open(filepath)
    page = doc[0]

    subject_code = extract_subject_code(page)
    title = extract_title(page)
    due_date = extract_due_date(page)
    description = extract_description(page)
    weighting = extract_weighting(page)

    doc.close()
    os.remove(filepath)  # Remove the file after processing

    # If any required field is missing, return False
    if not subject_code or not title or not due_date or not description or not weighting:
        return False

    # Return extracted data as a dictionary
    return {
        'filename': filename,
        'original_filename': file.filename,
        'subject_code': subject_code,
        'title': title,
        'description': description,
        'due_date': due_date.isoformat(),
        'weighting': weighting
    }
