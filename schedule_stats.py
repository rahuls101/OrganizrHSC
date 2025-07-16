from collections import Counter
from datetime import datetime

def calculate_weekly_stats(study_sessions): 

    total_sessions = len(study_sessions)

    total_hours = total_sessions * 2  # assuming 2 hours per session 

    subject_counts = Counter(studysession.assessment.subject_code for studysession in study_sessions)
    most_planned_subject = subject_counts.most_common(1)[0][0] if subject_counts else None
    subject_breakdown = {subject: count * 2 for subject, count in subject_counts.items()}

    return { 
        'total_hours': total_hours, 
        'total_sessions': total_sessions, 
        'most_subject': most_planned_subject,
        'subject_breakdown': subject_breakdown
    }
