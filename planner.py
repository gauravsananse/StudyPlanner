"""
Planner module for Study Planner Agent.
Contains scheduling algorithms, timetable generation, and strict business validation.
Validates dates, topic distributions, daily limits, and replanning proposals.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

VALID_WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def validate_plan_inputs(
    exam_date_str: str,
    subjects_dict: Dict[str, List[str]],
    available_days: List[str],
    daily_minutes: int,
    rest_days: Optional[List[str]] = None,
    current_date: Optional[date] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Strict validation of all user and agent-provided inputs for a study plan.
    Returns (is_valid, error_message, sanitized_dict).
    """
    today = current_date or date.today()
    rest_days = rest_days or []

    # 1. Validate exam_date
    if not exam_date_str or not isinstance(exam_date_str, str):
        return False, "Exam date must be a valid date string in YYYY-MM-DD format.", {}

    try:
        exam_date = datetime.strptime(exam_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return False, f"Invalid date format for exam date: '{exam_date_str}'. Expected YYYY-MM-DD.", {}

    if exam_date <= today:
        return False, f"Exam date ({exam_date}) must be in the future (after today: {today}).", {}

    # 2. Validate subjects and topics
    if not subjects_dict or not isinstance(subjects_dict, dict):
        return False, "You must provide at least one subject with topics.", {}

    sanitized_subjects: Dict[str, List[str]] = {}
    total_topics = 0

    for subject, raw_topics in subjects_dict.items():
        subject_name = str(subject).strip()
        if not subject_name:
            continue

        if isinstance(raw_topics, str):
            # Allow comma or newline separated string of topics
            topic_list = [t.strip() for t in raw_topics.replace("\n", ",").split(",") if t.strip()]
        elif isinstance(raw_topics, list):
            topic_list = [str(t).strip() for t in raw_topics if str(t).strip()]
        else:
            topic_list = []

        if topic_list:
            sanitized_subjects[subject_name] = topic_list
            total_topics += len(topic_list)

    if not sanitized_subjects or total_topics == 0:
        return False, "Please provide at least one subject containing at least one valid topic.", {}

    # 3. Validate available days
    if not available_days or not isinstance(available_days, list):
        return False, "Please select at least one available study day of the week.", {}

    sanitized_days = []
    for d in available_days:
        d_clean = str(d).strip().capitalize()
        if d_clean in VALID_WEEKDAYS:
            if d_clean not in sanitized_days:
                sanitized_days.append(d_clean)

    if not sanitized_days:
        return False, f"Available study days must be valid weekdays: {', '.join(VALID_WEEKDAYS)}.", {}

    # 4. Validate rest days
    sanitized_rest_days = []
    for rd in rest_days:
        rd_clean = str(rd).strip().capitalize()
        if rd_clean in VALID_WEEKDAYS and rd_clean not in sanitized_rest_days:
            sanitized_rest_days.append(rd_clean)

    # Ensure student didn't mark all available study days as rest days
    active_study_days = [d for d in sanitized_days if d not in sanitized_rest_days]
    if not active_study_days:
        return False, "All selected study days are marked as rest days. Please leave at least one study day active.", {}

    # 5. Validate study minutes
    try:
        daily_minutes_int = int(daily_minutes)
    except (ValueError, TypeError):
        return False, "Available study minutes per day must be an integer.", {}

    if daily_minutes_int < 15:
        return False, "Available study minutes must be at least 15 minutes per day.", {}
    if daily_minutes_int > 600:
        return False, "Available study minutes cannot exceed 600 minutes (10 hours) per day to prevent burnout.", {}

    sanitized_data = {
        "exam_date": exam_date.isoformat(),
        "subjects": sanitized_subjects,
        "available_days": sanitized_days,
        "daily_minutes": daily_minutes_int,
        "rest_days": sanitized_rest_days,
        "total_topics": total_topics,
    }
    return True, "", sanitized_data


def generate_schedule(
    exam_date_str: str,
    subjects_dict: Dict[str, List[str]],
    available_days: List[str],
    daily_minutes: int,
    rest_days: Optional[List[str]] = None,
    start_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Generates a balanced, structured study plan timetable.
    Interleaves subjects for optimal cognitive retention.
    Leaves exam day free for final rest/mindset.
    """
    today = start_date or date.today()
    rest_days = rest_days or []
    exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()

    # Create an interleaved queue of (subject, topic)
    # Collect lists of topics per subject
    subject_topics_queues: Dict[str, List[str]] = {
        s: list(topics) for s, topics in subjects_dict.items()
    }

    interleaved_topics: List[Tuple[str, str]] = []
    has_more = True
    while has_more:
        has_more = False
        for s, t_list in subject_topics_queues.items():
            if t_list:
                interleaved_topics.append((s, t_list.pop(0)))
                has_more = True

    # Identify all eligible study calendar dates from today up to exam_date - 1 day
    eligible_dates: List[date] = []
    curr = today
    # Don't place sessions on or after exam date
    end_date = exam_date - timedelta(days=1)
    if end_date < today:
        end_date = today

    while curr <= end_date:
        weekday_name = curr.strftime("%A")
        if weekday_name in available_days and weekday_name not in rest_days:
            eligible_dates.append(curr)
        curr += timedelta(days=1)

    if not eligible_dates:
        # If no days match (e.g., exam is tomorrow and today is not in available_days),
        # fallback to using today to at least provide study sessions
        eligible_dates = [today]

    sessions: List[Dict[str, Any]] = []

    # Decide session chunk length (e.g. 45-60 mins or full daily_minutes)
    # If daily_minutes >= 90 and we have multiple topics, we can split into 2 sessions per day
    sessions_per_day = 1
    session_duration = daily_minutes
    if daily_minutes >= 90 and len(interleaved_topics) > len(eligible_dates):
        sessions_per_day = 2
        session_duration = daily_minutes // 2

    topic_idx = 0
    total_unique_topics = len(interleaved_topics)

    for study_date in eligible_dates:
        date_iso = study_date.isoformat()

        for _ in range(sessions_per_day):
            if topic_idx < total_unique_topics:
                subj, top = interleaved_topics[topic_idx]
                sessions.append({
                    "date": date_iso,
                    "subject": subj,
                    "topic": top,
                    "duration_minutes": session_duration,
                    "status": "Planned",
                    "notes": "Core learning session",
                })
                topic_idx += 1
            else:
                # All unique topics covered! Schedule review / practice tests
                review_topic_idx = (topic_idx - total_unique_topics) % total_unique_topics
                subj, top = interleaved_topics[review_topic_idx]
                sessions.append({
                    "date": date_iso,
                    "subject": subj,
                    "topic": f"Review & Practice: {top}",
                    "duration_minutes": session_duration,
                    "status": "Planned",
                    "notes": "Review and revision session",
                })
                topic_idx += 1

    return sessions


def propose_replan_schedule(
    plan_data: Dict[str, Any],
    existing_sessions: List[Dict[str, Any]],
    current_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Generates an intelligent replanning proposal for unfinished topics.
    Preserves completed sessions. Reschedules missed or remaining planned sessions
    starting from today up to the exam date, adhering to available days and time limits.
    """
    today = current_date or date.today()
    exam_date_str = plan_data["exam_date"]
    exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    available_days = plan_data.get("available_days", VALID_WEEKDAYS[:5])
    daily_minutes = plan_data.get("daily_minutes", 60)
    rest_days = plan_data.get("rest_days", [])

    # Identify completed sessions vs unfinished sessions
    completed_sessions = [s for s in existing_sessions if s["status"] == "Completed"]
    completed_keys = {(s["subject"], s["topic"].replace("Review & Practice: ", "")) for s in completed_sessions}

    # Gather all topics from the original plan subjects
    subjects_dict: Dict[str, List[str]] = {}
    if "subjects" in plan_data:
        for subj in plan_data["subjects"]:
            s_name = subj["name"] if isinstance(subj, dict) else str(subj)
            t_names = subj.get("topics", []) if isinstance(subj, dict) else []
            # Keep only topics not already completed
            uncompleted_topics = [t for t in t_names if (s_name, t) not in completed_keys]
            if uncompleted_topics:
                subjects_dict[s_name] = uncompleted_topics

    # If all subject topics were completed or if subjects_dict is empty,
    # pull unfinished planned sessions
    if not subjects_dict:
        planned_sessions = [s for s in existing_sessions if s["status"] == "Planned"]
        for s in planned_sessions:
            clean_top = s["topic"].replace("Review & Practice: ", "")
            if (s["subject"], clean_top) not in completed_keys:
                subjects_dict.setdefault(s["subject"], []).append(clean_top)

    # If still empty (everything was completed!), create comprehensive final review sessions
    if not subjects_dict:
        all_subjects = [s["name"] if isinstance(s, dict) else str(s) for s in plan_data.get("subjects", [])]
        for s_name in all_subjects:
            subjects_dict[s_name] = ["Full Mock Exam & Synthesis"]

    # Generate new schedule starting from today
    new_sessions = generate_schedule(
        exam_date_str=exam_date_str,
        subjects_dict=subjects_dict,
        available_days=available_days,
        daily_minutes=daily_minutes,
        rest_days=rest_days,
        start_date=today,
    )

    days_left = (exam_date - today).days

    return {
        "success": True,
        "proposed_sessions": new_sessions,
        "new_sessions_count": len(new_sessions),
        "preserved_completed_count": len(completed_sessions),
        "days_until_exam": days_left,
        "start_date": today.isoformat(),
        "exam_date": exam_date_str,
        "summary": (
            f"Replanned schedule starting {today.isoformat()} until {exam_date_str}. "
            f"Preserved {len(completed_sessions)} completed session(s). "
            f"Created {len(new_sessions)} rescheduled session(s) over {days_left} remaining day(s)."
        ),
    }
