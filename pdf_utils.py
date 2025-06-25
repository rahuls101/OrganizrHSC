import os
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
from datetime import datetime
from auth import allowed_file 

# -----------------------------
# Individual extractors
# -----------------------------

def extract_subject_code(pdf): 
    subject_map = {
        "English": "ENG",
        "Mathematics": "MAT",
        "Physics": "PHY",
        # Add more HSC subjects as needed
    }
    text = pdf.get_text()
    for subjectname, code in subject_map.items():
        if subjectname in text:
            return code
    return "GEN"

def extract_due_date(pdf): 
    text_instances = pdf.search_for('Due Date')
    for inst in text_instances:
        extended_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)
        date = pdf.get_text("text", clip=extended_rect).strip()
        return date

def parse_date(date_str): 
    try: 
        return datetime.strptime(date_str, "%A, %d %B %Y")
    except ValueError: 
        return None

def extract_title(pdf): 
    text_instances = pdf.search_for('Task title')
    for inst in text_instances:
        extended_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)
        title = pdf.get_text("text", clip=extended_rect).strip()
        return title

def extract_description(pdf): 
    return 'Placeholder description'

# -----------------------------
# Main processor
# -----------------------------

def process_uploaded_files(files, upload_folder):
    results = []

    for file in files:
        if not file or not allowed_file(file.filename):
            results.append({
                'filename': file.filename if file else 'unknown',
                'error': 'Invalid file type'
            })
            continue

        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        try:
            doc = fitz.open(filepath)
            page = doc[0]

            subject_code = extract_subject_code(page)
            title = extract_title(page)
            due_date_raw = extract_due_date(page)
            due_date = parse_date(due_date_raw)
            description = extract_description(page)

            doc.close()
            os.remove(filepath)

            results.append({
                'filename': filename,
                'original_filename': file.filename,
                'subject_code': subject_code,
                'title': title,
                'description': description,
                'due_date': due_date.isoformat() if due_date else None
            })

        except Exception as e:
            results.append({
                'filename': filename,
                'original_filename': file.filename,
                'error': str(e)
            })

        finally:
            try:
                doc.close()
            except:
                pass
            try:
                os.remove(filepath)
            except:
                pass

    return results
