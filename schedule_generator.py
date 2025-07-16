from datetime import timedelta, datetime
from models import db, Assessment, StudySession, User
import random 

def generate_schedule_for_new_assessments(user_id):
    user = User.query.get(user_id)
    if not user:
        return

    assessments = user.assessments  

    for assessment in assessments:
        existing_sessions = StudySession.query.filter_by(
            user_id=user_id,
            assessment_id=assessment.id
        ).count()

        if existing_sessions >= 6:
            continue  # already has study sessions

        due_date = assessment.due_date.date()
        today = datetime.now().date()
        days_available = (due_date - today).days

        # handle due date today case
        if days_available <= 0:
            continue

        interval_days = max(days_available // 6, 1)
        #session_times = [7, 9, 11, 13, 15, 17, 19, 21]  # INCLUDING SCHOOL HOURS
        session_times = [7, 17, 19, 21]  # NOT INCLUDING SCHOOL HOURS

        sessions_created = 0
        offset = 1  # dont schedule on the due date

        for i in range(6):
            session_date = due_date - timedelta(days=offset + i * interval_days)

            #shuffle the sessiontimes for variety 

            random_times = session_times.copy()
            random.shuffle(random_times)


            for session_time in random_times:
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
                break  # Move to next session date

    db.session.commit()
