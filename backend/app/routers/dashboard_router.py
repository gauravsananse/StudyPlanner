import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..database import get_db_connection
from ..schemas import GoalCreate, GoalOut

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("")
def get_dashboard_data(current_user: dict = Depends(get_current_user)):
    """Fetches high-level metrics, today's time slots, goals, and upcoming exam countdowns."""
    user_id = current_user["id"]
    today_str = date.today().isoformat()
    today = date.today()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Total sessions and hours
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_sessions,
                SUM(duration_minutes) as total_minutes,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_sessions,
                SUM(CASE WHEN status = 'Completed' THEN duration_minutes ELSE 0 END) as completed_minutes
            FROM sessions
            WHERE user_id = ?;
            """,
            (user_id,),
        )
        stats = cursor.fetchone()

        total_sessions = stats["total_sessions"] or 0
        total_hours = round((stats["total_minutes"] or 0) / 60.0, 1)
        completed_sessions = stats["completed_sessions"] or 0
        completed_hours = round((stats["completed_minutes"] or 0) / 60.0, 1)

        # 2. Today's sessions with dynamic time slots
        cursor.execute(
            """
            SELECT id, plan_id, date, time_slot, subject, topic, duration_minutes, actionable_task, status
            FROM sessions
            WHERE user_id = ? AND date = ?
            ORDER BY time_slot ASC, id ASC;
            """,
            (user_id, today_str),
        )
        today_sessions = [dict(s) for s in cursor.fetchall()]

        # 2b. Overdue / Missed sessions across plans (status = 'Missed' or (status = 'Planned' and date < today_str))
        cursor.execute(
            """
            SELECT s.id, s.plan_id, s.date, s.time_slot, s.subject, s.topic, s.duration_minutes, p.title as plan_title
            FROM sessions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.user_id = ? AND (s.status = 'Missed' OR (s.status = 'Planned' AND s.date < ?))
            ORDER BY s.date DESC;
            """,
            (user_id, today_str),
        )
        missed_sessions = [dict(s) for s in cursor.fetchall()]

        # 3. Upcoming exams with days left
        cursor.execute(
            """
            SELECT id, title, exam_date, daily_hours
            FROM plans
            WHERE user_id = ?
            ORDER BY exam_date ASC;
            """,
            (user_id,),
        )
        plan_rows = cursor.fetchall()
        upcoming_exams = []
        for p in plan_rows:
            try:
                ex_d = datetime.strptime(p["exam_date"], "%Y-%m-%d").date()
                days_left = (ex_d - today).days
            except Exception:
                days_left = 0
            upcoming_exams.append({
                "id": p["id"],
                "title": p["title"],
                "exam_date": p["exam_date"],
                "daily_hours": p["daily_hours"],
                "days_left": days_left,
            })

        # 4. User goals
        cursor.execute(
            """
            SELECT id, title, target_hours, achieved_hours, is_completed, created_at
            FROM goals
            WHERE user_id = ?
            ORDER BY id DESC;
            """,
            (user_id,),
        )
        goals = [
            GoalOut(
                id=g["id"],
                title=g["title"],
                target_hours=g["target_hours"],
                achieved_hours=g["achieved_hours"],
                is_completed=bool(g["is_completed"]),
                created_at=g["created_at"],
            )
            for g in cursor.fetchall()
        ]

        return {
            "user": current_user,
            "metrics": {
                "total_plans": len(upcoming_exams),
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "total_hours": total_hours,
                "completed_hours": completed_hours,
                "missed_sessions_count": len(missed_sessions),
                "completion_rate": round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0,
            },
            "today_sessions": today_sessions,
            "missed_sessions": missed_sessions,
            "upcoming_exams": upcoming_exams,
            "goals": goals,
        }


@router.post("/goals", response_model=GoalOut)
def create_goal(goal_in: GoalCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO goals (user_id, title, target_hours, achieved_hours, is_completed, created_at)
            VALUES (?, ?, ?, 0.0, 0, ?);
            """,
            (user_id, goal_in.title.strip(), goal_in.target_hours, now_iso),
        )
        goal_id = cursor.lastrowid
        conn.commit()

        return GoalOut(
            id=goal_id,
            title=goal_in.title.strip(),
            target_hours=goal_in.target_hours,
            achieved_hours=0.0,
            is_completed=False,
            created_at=now_iso,
        )


@router.patch("/goals/{goal_id}/toggle")
def toggle_goal(goal_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, is_completed FROM goals WHERE id = ? AND user_id = ?;", (goal_id, user_id))
        g = cursor.fetchone()
        if not g:
            raise HTTPException(status_code=404, detail="Goal not found.")

        new_val = 0 if g["is_completed"] else 1
        cursor.execute("UPDATE goals SET is_completed = ? WHERE id = ?;", (new_val, goal_id))
        conn.commit()
        return {"success": True, "goal_id": goal_id, "is_completed": bool(new_val)}
