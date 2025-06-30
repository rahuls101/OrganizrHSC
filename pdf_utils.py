import os
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
from datetime import datetime

# -----------------------------
# Individual extractors
# -----------------------------

def extract_subject_code(pdf): 
    subject_map = {
        "English": "ENG",
        "Mathematics": "MAT",
        "Physics": "PHY",
        "Chemistry": "CHE",
        "Biology": "BIO",
        "Economics": "ECO",
        "Business Studies": "BUS",
        "Legal Studies": "LEG",
        "Modern History": "MOD",
        "PDHPE": "PDH",
        # Add more HSC subjects as needed
    }
    text = pdf.get_text()
    for subjectname, code in subject_map.items():
        if subjectname in text:
            return code
    return False

def extract_due_date(pdf): 
    text_instances = pdf.search_for('Due Date')
    for inst in text_instances:
        rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)
        raw = pdf.get_text("text", clip=rect).strip()
        try: 
            return datetime.strptime(raw, "%A, %d %B %Y")
        except ValueError: 
            return False 
    return False 

def extract_title(pdf): 
    text_instances = pdf.search_for('Task title')
    for inst in text_instances:
        extended_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)
        title = pdf.get_text("text", clip=extended_rect).strip()
        return title if title else False 
    return False 

def extract_description(pdf): 
    return 'Placeholder description'

# -----------------------------
# Main processor
# -----------------------------

def process_file(file, upload_folder):

    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)


    doc = fitz.open(filepath)
    page = doc[0]


    subject_code = extract_subject_code(page)
    title = extract_title(page)
    due_date = extract_due_date(page)
    description = extract_description(page)

    doc.close()
    os.remove(filepath)

    
    if not subject_code or not title or not due_date or not description: 
        return False
    
    return {
        'filename': filename,
        'original_filename': file.filename, 
        'subject_code': subject_code, 
        'title': title, 
        'description': description, 
        'due_date': due_date.isoformat()
    }
