import os
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
from datetime import datetime
from subject_config import name_to_code

# -----------------------------
# Individual extractors
# -----------------------------

def extract_subject_code(pdf): 
    text = pdf.get_text().lower()

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
    
    #if its not a maths or english subjects just find code normally

    for name, code in name_to_code.items():
        if name.lower() in text:
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
