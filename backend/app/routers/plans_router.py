import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..database import get_db_connection
from ..gemini_service import generate_study_plan_ai, reschedule_missed_sessions
from ..schemas import (
    PlanCreateRequest,
    PlanGenerateRequest,
    PlanOut,
    SessionItem,
    SessionOut,
)

router = APIRouter(prefix="/api/plans", tags=["Study Plans"])


@router.post("/generate")
def generate_plan_preview(
    req: PlanGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generates an AI-powered study plan preview with dynamic time slots and blackout weeks."""
    subjects_data = [{"name": s.name, "topics": s.topics} for s in req.subjects]
    plan_result = generate_study_plan_ai(
        title=req.title,
        exam_date_str=req.exam_date,
        subjects=subjects_data,
        daily_hours=req.daily_hours,
        study_days=req.study_days,
        preferred_slots=req.preferred_slots,
        unavailable_weeks=req.unavailable_weeks,
    )
    return plan_result


@router.post("", response_model=Dict[str, Any])
def save_plan(
    plan_in: PlanCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Saves a confirmed study plan and sessions to the SQLite database."""
    user_id = current_user["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Insert plan
        cursor.execute(
            """
            INSERT INTO plans (user_id, title, exam_date, daily_hours, preferred_slots, study_days, unavailable_weeks, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?);
            """,
            (
                user_id,
                plan_in.title.strip(),
                plan_in.exam_date.strip(),
                plan_in.daily_hours,
                json.dumps(plan_in.preferred_slots),
                json.dumps(plan_in.study_days or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]),
                json.dumps(plan_in.unavailable_weeks or []),
                now_iso,
            ),
        )
        plan_id = cursor.lastrowid



        # Insert subjects
        for s in plan_in.subjects:
            cursor.execute(
                """
                INSERT INTO subjects (plan_id, name, topics)
                VALUES (?, ?, ?);
                """,
                (plan_id, s.name.strip(), json.dumps(s.topics)),
            )

        # Insert sessions
        for sess in plan_in.sessions:
            cursor.execute(
                """
                INSERT INTO sessions (plan_id, user_id, date, time_slot, subject, topic, duration_minutes, actionable_task, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Planned');
                """,
                (
                    plan_id,
                    user_id,
                    sess.date,
                    sess.time_slot,
                    sess.subject,
                    sess.topic,
                    sess.duration_minutes,
                    sess.actionable_task or "",
                ),
            )

        conn.commit()
        return {
            "success": True,
            "message": "Study plan and sessions saved successfully!",
            "plan_id": plan_id,
            "total_sessions": len(plan_in.sessions),
        }


@router.get("", response_model=List[PlanOut])
def get_user_plans(current_user: dict = Depends(get_current_user)):
    """Retrieves all study plans created by the logged-in user."""
    user_id = current_user["id"]
    today = date.today()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM plans WHERE user_id = ? ORDER BY id DESC;",
            (user_id,),
        )
        plan_rows = cursor.fetchall()

        result = []
        for p in plan_rows:
            p_id = p["id"]
            cursor.execute("SELECT COUNT(*) as cnt FROM sessions WHERE plan_id = ?;", (p_id,))
            total_sessions = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM sessions WHERE plan_id = ? AND status = 'Completed';", (p_id,))
            completed_sessions = cursor.fetchone()["cnt"]

            try:
                exam_d = datetime.strptime(p["exam_date"], "%Y-%m-%d").date()
                days_left = max(0, (exam_d - today).days)
            except Exception:
                days_left = 0

            preferred_slots = json.loads(p["preferred_slots"]) if p["preferred_slots"] else []
            study_days = json.loads(p["study_days"]) if ("study_days" in p.keys() and p["study_days"]) else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            unavailable_weeks = json.loads(p["unavailable_weeks"]) if ("unavailable_weeks" in p.keys() and p["unavailable_weeks"]) else []

            result.append(
                PlanOut(
                    id=p["id"],
                    title=p["title"],
                    exam_date=p["exam_date"],
                    daily_hours=p["daily_hours"],
                    preferred_slots=preferred_slots,
                    study_days=study_days,
                    unavailable_weeks=unavailable_weeks,
                    status=p["status"],
                    created_at=p["created_at"],
                    total_sessions=total_sessions,
                    completed_sessions=completed_sessions,
                    days_left=days_left,
                )
            )
        return result


@router.get("/{plan_id}")
def get_plan_details(plan_id: int, current_user: dict = Depends(get_current_user)):
    """Retrieves a study plan with all its scheduled dynamic sessions."""
    user_id = current_user["id"]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plans WHERE id = ? AND user_id = ?;", (plan_id, user_id))
        plan = cursor.fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found.")

        cursor.execute(
            "SELECT * FROM sessions WHERE plan_id = ? ORDER BY date ASC, time_slot ASC;",
            (plan_id,),
        )
        sessions = cursor.fetchall()

        cursor.execute("SELECT * FROM subjects WHERE plan_id = ?;", (plan_id,))
        subjects = cursor.fetchall()

        study_days = json.loads(plan["study_days"]) if ("study_days" in plan.keys() and plan["study_days"]) else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        unavailable_weeks = json.loads(plan["unavailable_weeks"]) if ("unavailable_weeks" in plan.keys() and plan["unavailable_weeks"]) else []

        return {
            "plan": {
                "id": plan["id"],
                "title": plan["title"],
                "exam_date": plan["exam_date"],
                "daily_hours": plan["daily_hours"],
                "preferred_slots": json.loads(plan["preferred_slots"]) if plan["preferred_slots"] else [],
                "study_days": study_days,
                "unavailable_weeks": unavailable_weeks,
                "status": plan["status"],
            },
            "subjects": [{"id": s["id"], "name": s["name"], "topics": json.loads(s["topics"])} for s in subjects],
            "sessions": [dict(s) for s in sessions],
        }



@router.patch("/sessions/{session_id}/toggle")
def toggle_session_status(session_id: int, current_user: dict = Depends(get_current_user)):
    """Toggles session status between Planned and Completed."""
    user_id = current_user["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ? AND user_id = ?;", (session_id, user_id))
        sess = cursor.fetchone()
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found.")

        new_status = "Completed" if sess["status"] == "Planned" else "Planned"
        completed_at = now_iso if new_status == "Completed" else None

        cursor.execute(
            """
            UPDATE sessions
            SET status = ?, completed_at = ?
            WHERE id = ?;
            """,
            (new_status, completed_at, session_id),
        )
        conn.commit()

        return {
            "success": True,
            "session_id": session_id,
            "new_status": new_status,
            "completed_at": completed_at,
        }


@router.post("/{plan_id}/reschedule-missed")
def reschedule_plan_missed_sessions(
    plan_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Intelligently reschedules all missed or uncompleted sessions up to the exam date.
    Preserves all completed sessions and redistributes remaining topics across upcoming days.
    """
    user_id = current_user["id"]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plans WHERE id = ? AND user_id = ?;", (plan_id, user_id))
        plan = cursor.fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found.")

        cursor.execute("SELECT * FROM subjects WHERE plan_id = ?;", (plan_id,))
        subjects = [{"name": s["name"], "topics": json.loads(s["topics"])} for s in cursor.fetchall()]

        cursor.execute("SELECT * FROM sessions WHERE plan_id = ? ORDER BY date ASC, time_slot ASC;", (plan_id,))
        existing_sessions = [dict(s) for s in cursor.fetchall()]

        preferred_slots = json.loads(plan["preferred_slots"]) if plan["preferred_slots"] else []
        study_days = json.loads(plan["study_days"]) if ("study_days" in plan.keys() and plan["study_days"]) else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        unavailable_weeks = json.loads(plan["unavailable_weeks"]) if ("unavailable_weeks" in plan.keys() and plan["unavailable_weeks"]) else []

        replan_res = reschedule_missed_sessions(
            plan_title=plan["title"],
            exam_date_str=plan["exam_date"],
            subjects=subjects,
            existing_sessions=existing_sessions,
            preferred_slots=preferred_slots,
            daily_hours=plan["daily_hours"],
            study_days=study_days,
            unavailable_weeks=unavailable_weeks,
        )

        # Atomic replacement: Delete only UNCOMPLETED sessions (Completed are preserved)
        cursor.execute(
            "DELETE FROM sessions WHERE plan_id = ? AND user_id = ? AND status != 'Completed';",
            (plan_id, user_id),
        )

        # Insert new rescheduled sessions
        for sess in replan_res["rescheduled_sessions"]:
            cursor.execute(
                """
                INSERT INTO sessions (plan_id, user_id, date, time_slot, subject, topic, duration_minutes, actionable_task, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Planned');
                """,
                (
                    plan_id,
                    user_id,
                    sess["date"],
                    sess["time_slot"],
                    sess["subject"],
                    sess["topic"],
                    sess["duration_minutes"],
                    sess.get("actionable_task", ""),
                ),
            )

        conn.commit()

        # Fetch refreshed sessions
        cursor.execute("SELECT * FROM sessions WHERE plan_id = ? ORDER BY date ASC, time_slot ASC;", (plan_id,))
        refreshed_sessions = [dict(s) for s in cursor.fetchall()]

        return {
            "success": True,
            "message": replan_res["message"],
            "preserved_completed_count": replan_res["completed_count"],
            "rescheduled_count": replan_res["rescheduled_count"],
            "days_until_exam": replan_res["days_until_exam"],
            "sessions": refreshed_sessions,
        }


@router.patch("/sessions/{session_id}/miss")
def mark_session_missed(session_id: int, current_user: dict = Depends(get_current_user)):
    """Marks a session status explicitly as Missed."""
    user_id = current_user["id"]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ? AND user_id = ?;", (session_id, user_id))
        sess = cursor.fetchone()
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found.")

        cursor.execute("UPDATE sessions SET status = 'Missed' WHERE id = ?;", (session_id,))
        conn.commit()
        return {"success": True, "session_id": session_id, "new_status": "Missed"}


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, current_user: dict = Depends(get_current_user)):
    """Deletes a study plan and associated sessions."""
    user_id = current_user["id"]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM plans WHERE id = ? AND user_id = ?;", (plan_id, user_id))
        conn.commit()
        return {"success": True, "message": "Plan deleted."}

