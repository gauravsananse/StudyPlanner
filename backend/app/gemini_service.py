"""
High-Speed Gemini AI service for Study Planner AI.
Combines Gemini Flash Lite cognitive pedagogical intelligence with a microsecond
Python dynamic scheduling engine for sub-3-second schedule generation.
"""

import json
import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .config import GEMINI_API_KEY

FAST_GEMINI_MODEL = "gemini-flash-lite-latest"
FALLBACK_GEMINI_MODEL = "gemini-3.5-flash"


def generate_study_plan_ai(
    title: str,
    exam_date_str: str,
    subjects: List[Dict[str, Any]],
    daily_hours: float = 2.0,
    study_days: Optional[List[str]] = None,
    preferred_slots: Optional[List[str]] = None,
    unavailable_weeks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    High-speed AI study plan generator.
    1. Queries Gemini Flash Lite for topic-by-topic pedagogical directives (< 3s).
    2. Maps tasks instantly to exact calendar dates and dynamic time slots (< 5ms).
    """
    study_days = study_days or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    preferred_slots = preferred_slots or [
        "Morning (09:00 - 10:30 AM)",
        "Evening (06:30 - 08:00 PM)",
    ]
    unavailable_weeks = unavailable_weeks or []
    today = date.today()

    try:
        exam_date = datetime.strptime(exam_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        exam_date = today + timedelta(days=21)

    # Format topic summaries
    topics_list = []
    subjects_summary = []
    for s in subjects:
        s_name = s.get("name", "General").strip()
        t_list = [t.strip() for t in s.get("topics", []) if t.strip()]
        if t_list:
            subjects_summary.append(f"{s_name}: {', '.join(t_list)}")
            for t in t_list:
                topics_list.append({"subject": s_name, "topic": t})

    ai_overview = f"Targeted exam preparation roadmap for {title}"
    ai_tasks: Dict[str, str] = {}
    ai_source = "Structured Engine"

    # Call Gemini Flash Lite for pedagogical tasks if API key exists
    if GEMINI_API_KEY and GEMINI_API_KEY.strip() and topics_list:
        prompt = f"""You are an elite academic tutor.
Analyze these subjects and topics for an upcoming exam ({title}):
{chr(10).join(f"- {s}" for s in subjects_summary)}

Return a concise, raw JSON object with:
1. "overview": An inspiring, 1-sentence exam prep strategy.
2. "tasks": An object mapping each topic name to a concrete, 1-sentence actionable study directive (e.g. "Solve 10 practice problems and review core theorems").

Respond with raw JSON only (no markdown, no code blocks):
{{
  "overview": "...",
  "tasks": {{
    "Topic Name": "Concrete action directive"
  }}
}}"""
        try:
            from google import genai

            client = genai.Client(api_key=GEMINI_API_KEY.strip())
            # Try fastest model first
            try:
                resp = client.models.generate_content(
                    model=FAST_GEMINI_MODEL,
                    contents=prompt,
                )
            except Exception:
                resp = client.models.generate_content(
                    model=FALLBACK_GEMINI_MODEL,
                    contents=prompt,
                )

            raw_text = resp.text.strip()
            raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)
            parsed = json.loads(raw_text)

            ai_overview = parsed.get("overview", ai_overview)
            ai_tasks = parsed.get("tasks", {})
            ai_source = "Gemini AI"
        except Exception as e:
            print(f"[Gemini Service Note]: AI call failed ({e}), using instant rule-based tasks.")

    # Microsecond Schedule Synthesizer
    sessions = build_dynamic_sessions(
        topics_list=topics_list,
        today=today,
        exam_date=exam_date,
        study_days=study_days,
        preferred_slots=preferred_slots,
        daily_hours=daily_hours,
        ai_tasks=ai_tasks,
        unavailable_weeks=unavailable_weeks,
    )

    return {
        "source": ai_source,
        "model": FAST_GEMINI_MODEL if ai_source == "Gemini AI" else "Fast Rule Engine",
        "overview": ai_overview,
        "sessions": sessions,
    }


def build_dynamic_sessions(
    topics_list: List[Dict[str, str]],
    today: date,
    exam_date: date,
    study_days: List[str],
    preferred_slots: List[str],
    daily_hours: float,
    ai_tasks: Dict[str, str],
    unavailable_weeks: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Generates interleaved sessions with dynamic time slots instantly, respecting unavailable weeks."""
    if not topics_list:
        topics_list = [{"subject": "General", "topic": "Core Fundamentals"}]

    # Interleave topics across subjects
    by_subject: Dict[str, List[str]] = {}
    for item in topics_list:
        by_subject.setdefault(item["subject"], []).append(item["topic"])

    interleaved_pairs: List[tuple] = []
    has_more = True
    while has_more:
        has_more = False
        for s_name, t_queue in by_subject.items():
            if t_queue:
                interleaved_pairs.append((s_name, t_queue.pop(0)))
                has_more = True

    # Find available calendar dates (filtering out study_days and unavailable_weeks)
    eligible_dates: List[date] = []
    curr = today
    end_date = exam_date - timedelta(days=1)
    if end_date < today:
        end_date = today

    while curr <= end_date:
        is_blackout = False
        if unavailable_weeks:
            for uw in unavailable_weeks:
                try:
                    w_start = datetime.strptime(str(uw.get("startDate", "")).strip(), "%Y-%m-%d").date()
                    w_end = datetime.strptime(str(uw.get("endDate", "")).strip(), "%Y-%m-%d").date()
                    if w_start <= curr <= w_end:
                        is_blackout = True
                        break
                except Exception:
                    pass

        if not is_blackout and curr.strftime("%A") in study_days:
            eligible_dates.append(curr)
        curr += timedelta(days=1)

    if not eligible_dates:
        eligible_dates = [today]


    # Clean slots
    clean_slots = []
    for s in preferred_slots:
        if "(" in s and ")" in s:
            match = re.search(r"\((.*?)\)", s)
            clean_slots.append(match.group(1) if match else s)
        else:
            clean_slots.append(s)

    if not clean_slots:
        clean_slots = ["09:00 - 10:30 AM", "06:30 - 08:00 PM"]

    sessions: List[Dict[str, Any]] = []
    topic_idx = 0
    total_unique = len(interleaved_pairs)
    duration_mins = int(daily_hours * 60) if daily_hours <= 1.5 else 90

    for study_date in eligible_dates:
        slot = clean_slots[len(sessions) % len(clean_slots)]
        is_final_review = (exam_date - study_date).days <= 3

        if topic_idx < total_unique:
            subj, top = interleaved_pairs[topic_idx]
            task_desc = ai_tasks.get(top) or f"Master key concepts in {top} and solve targeted exercises."
            sessions.append({
                "date": study_date.isoformat(),
                "time_slot": slot,
                "subject": subj,
                "topic": top,
                "duration_minutes": duration_mins,
                "actionable_task": task_desc,
            })
            topic_idx += 1
        elif is_final_review:
            # Final mock exam and synthesis
            subj, top = interleaved_pairs[topic_idx % total_unique]
            sessions.append({
                "date": study_date.isoformat(),
                "time_slot": slot,
                "subject": subj,
                "topic": f"Final Synthesis & Mock Test: {subj}",
                "duration_minutes": duration_mins,
                "actionable_task": "Timed exam simulation, review mistake log, and formula sheet memorization.",
            })
            topic_idx += 1
        else:
            # Active recall & spaced repetition
            rev_idx = (topic_idx - total_unique) % total_unique
            subj, top = interleaved_pairs[rev_idx]
            sessions.append({
                "date": study_date.isoformat(),
                "time_slot": slot,
                "subject": subj,
                "topic": f"Review & Spaced Recall: {top}",
                "duration_minutes": duration_mins,
                "actionable_task": f"Flashcards review and self-testing on past mistakes in {top}.",
            })
            topic_idx += 1

    return sessions


def reschedule_missed_sessions(
    plan_title: str,
    exam_date_str: str,
    subjects: List[Dict[str, Any]],
    existing_sessions: List[Dict[str, Any]],
    preferred_slots: Optional[List[str]] = None,
    daily_hours: float = 2.0,
    study_days: Optional[List[str]] = None,
    current_date: Optional[date] = None,
    unavailable_weeks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Intelligently reschedules missed and pending study sessions up until the exam date.
    Preserves all completed sessions and re-interleaves remaining topics across
    the remaining calendar dates, respecting blackout/unavailable weeks.
    """
    today = current_date or date.today()
    study_days = study_days or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    preferred_slots = preferred_slots or ["09:00 - 10:30 AM", "06:30 - 08:00 PM"]
    unavailable_weeks = unavailable_weeks or []

    try:
        exam_date = datetime.strptime(exam_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        exam_date = today + timedelta(days=14)

    # 1. Identify completed vs uncompleted
    completed_sessions = [s for s in existing_sessions if s.get("status") == "Completed"]
    completed_topic_keys = {
        (s.get("subject"), s.get("topic", "").replace("Review & Spaced Recall: ", "").replace("Final Synthesis & Mock Test: ", ""))
        for s in completed_sessions
    }

    # 2. Extract existing actionable tasks to preserve AI pedagogical insights
    cached_tasks: Dict[str, str] = {}
    for s in existing_sessions:
        top = s.get("topic", "")
        task = s.get("actionable_task", "")
        if top and task:
            clean_top = top.replace("Review & Spaced Recall: ", "").replace("Final Synthesis & Mock Test: ", "")
            cached_tasks[clean_top] = task
            cached_tasks[top] = task

    # 3. Collect uncompleted topics from subjects
    topics_list = []
    for s in subjects:
        s_name = s.get("name", "General").strip()
        t_raw = s.get("topics", [])
        if isinstance(t_raw, str):
            try:
                t_list = json.loads(t_raw)
            except Exception:
                t_list = [t.strip() for t in t_raw.split(",") if t.strip()]
        else:
            t_list = [t.strip() for t in t_raw if str(t).strip()]

        for t in t_list:
            if (s_name, t) not in completed_topic_keys:
                topics_list.append({"subject": s_name, "topic": t})

    # If all primary topics completed, look at any planned sessions that weren't completed
    if not topics_list:
        uncompleted_sessions = [s for s in existing_sessions if s.get("status") != "Completed"]
        for s in uncompleted_sessions:
            clean_top = s.get("topic", "").replace("Review & Spaced Recall: ", "").replace("Final Synthesis & Mock Test: ", "")
            topics_list.append({"subject": s.get("subject", "General"), "topic": clean_top})

    # If still empty, create final synthesis mock sessions
    if not topics_list:
        for s in subjects:
            s_name = s.get("name", "General").strip()
            topics_list.append({"subject": s_name, "topic": "Final Comprehensive Review & Mock Test"})

    # 4. Generate dynamic sessions starting from today up to exam date
    rescheduled_sessions = build_dynamic_sessions(
        topics_list=topics_list,
        today=today,
        exam_date=exam_date,
        study_days=study_days,
        preferred_slots=preferred_slots,
        daily_hours=daily_hours,
        ai_tasks=cached_tasks,
        unavailable_weeks=unavailable_weeks,
    )

    days_until_exam = max(0, (exam_date - today).days)

    return {
        "success": True,
        "completed_count": len(completed_sessions),
        "rescheduled_count": len(rescheduled_sessions),
        "days_until_exam": days_until_exam,
        "rescheduled_sessions": rescheduled_sessions,
        "message": (
            f"Successfully rescheduled {len(rescheduled_sessions)} sessions up to {exam_date_str}. "
            f"Preserved {len(completed_sessions)} completed sessions."
        ),
    }

