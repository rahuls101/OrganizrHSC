from datetime import timedelta, datetime
from models import db, Assessment, StudySession, User
import random

def generate_schedule_for_new_assessments(user_id):
    user = User.query.get(user_id)

    assessments = user.assessments  

    for assessment in assessments:
        # Decide number of sessions based on weighting
        if assessment.weighting >= 35:
            session_target = 8
        elif assessment.weighting >= 25:
            session_target = 6
        else:
            session_target = 4

        existing_sessions = StudySession.query.filter_by(
            user_id=user_id,
            assessment_id=assessment.id
        ).count()

        if existing_sessions >= session_target:
            continue  # already has enough sessions

        due_date = assessment.due_date.date()
        today = datetime.now().date()
        days_available = (due_date - today).days

        if days_available <= 0:
            continue  # can't schedule in the past or on the due date

        interval_days = max(days_available // session_target, 1)

        offset = 1  # don't schedule on the due date
        sessions_created = 0

        i = 0 
        while sessions_created < session_target and i < session_target * 2:
            random_offset = random.randint(0,2)
            session_date = due_date - timedelta(days=(offset + i * interval_days) + random_offset)

            if session_date.weekday() >= 5:  # weekend
                session_times = [7, 9, 11, 13, 15, 17, 19, 21]
            else:
                session_times = [7, 17, 19, 21]  # weekday

            random.shuffle(session_times)

            for session_time in session_times:
                conflict = StudySession.query.filter_by(
                    user_id=user_id,
                    date=session_date,
                    time=session_time
                ).first()

                if conflict:
                    continue

                new_session = StudySession(
                    user_id=user_id,
                    assessment_id=assessment.id,
                    date=session_date,
                    time=session_time
                )
                db.session.add(new_session)
                sessions_created += 1
                break  # move to next session date
            
            i += 1


    db.session.commit()
