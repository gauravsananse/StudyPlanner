"""
Database module for Study Planner Agent.
Provides SQLite storage for active study plans, subjects, topics, and sessions.
Uses parameterized queries to prevent SQL injection and maintains ACID safety.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = "study_planner.db"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Creates a database connection with row factory configured."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the database schema if tables do not exist."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                available_days TEXT NOT NULL,
                daily_minutes INTEGER NOT NULL,
                rest_days TEXT DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        # Subjects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE
            );
        """)

        # Topics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                estimated_minutes INTEGER NOT NULL DEFAULT 60,
                FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            );
        """)

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Planned',
                completed_at TEXT,
                notes TEXT,
                FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE
            );
        """)
        conn.commit()


def get_active_plan(db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Fetches the currently active plan, including its subjects and topics."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM plans WHERE is_active = 1 ORDER BY id DESC LIMIT 1;"
        )
        plan_row = cursor.fetchone()
        if not plan_row:
            return None

        plan_id = plan_row["id"]

        # Fetch subjects and their topics
        cursor.execute("SELECT * FROM subjects WHERE plan_id = ? ORDER BY id ASC;", (plan_id,))
        subject_rows = cursor.fetchall()

        subjects_data = []
        for s_row in subject_rows:
            cursor.execute(
                "SELECT * FROM topics WHERE subject_id = ? ORDER BY id ASC;",
                (s_row["id"],),
            )
            topic_rows = cursor.fetchall()
            subjects_data.append({
                "id": s_row["id"],
                "name": s_row["name"],
                "topics": [t["name"] for t in topic_rows],
            })

        available_days = json.loads(plan_row["available_days"])
        rest_days = json.loads(plan_row["rest_days"]) if plan_row["rest_days"] else []

        return {
            "id": plan_id,
            "title": plan_row["title"],
            "exam_date": plan_row["exam_date"],
            "available_days": available_days,
            "daily_minutes": plan_row["daily_minutes"],
            "rest_days": rest_days,
            "created_at": plan_row["created_at"],
            "subjects": subjects_data,
        }


def save_plan(
    exam_date: str,
    subjects_dict: Dict[str, List[str]],
    available_days: List[str],
    daily_minutes: int,
    rest_days: Optional[List[str]] = None,
    sessions: Optional[List[Dict[str, Any]]] = None,
    title: str = "Active Study Plan",
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """
    Saves a newly confirmed study plan.
    Deactivates any previous plan and inserts the new plan, subjects, topics, and initial sessions.
    """
    init_db(db_path)
    rest_days = rest_days or []
    now_iso = datetime.now().isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Deactivate existing plans
        cursor.execute("UPDATE plans SET is_active = 0 WHERE is_active = 1;")

        # Insert new plan
        cursor.execute(
            """
            INSERT INTO plans (title, exam_date, available_days, daily_minutes, rest_days, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?);
            """,
            (
                title,
                exam_date,
                json.dumps(available_days),
                daily_minutes,
                json.dumps(rest_days),
                now_iso,
            ),
        )
        plan_id = cursor.lastrowid

        # Insert subjects and topics
        for subj_name, topics in subjects_dict.items():
            cursor.execute(
                "INSERT INTO subjects (plan_id, name) VALUES (?, ?);",
                (plan_id, subj_name.strip()),
            )
            subject_id = cursor.lastrowid
            for top_name in topics:
                if top_name.strip():
                    cursor.execute(
                        """
                        INSERT INTO topics (plan_id, subject_id, name, estimated_minutes)
                        VALUES (?, ?, ?, ?);
                        """,
                        (plan_id, subject_id, top_name.strip(), daily_minutes),
                    )

        # Insert sessions if provided
        if sessions:
            for s in sessions:
                cursor.execute(
                    """
                    INSERT INTO sessions (plan_id, date, subject, topic, duration_minutes, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        plan_id,
                        s["date"],
                        s["subject"],
                        s["topic"],
                        s["duration_minutes"],
                        s.get("status", "Planned"),
                        s.get("notes", ""),
                    ),
                )

        conn.commit()
        return plan_id


def get_sessions(
    plan_id: Optional[int] = None,
    status: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """Retrieves sessions for a plan, ordered by date ascending."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        if plan_id is None:
            # Get active plan id
            cursor.execute("SELECT id FROM plans WHERE is_active = 1 ORDER BY id DESC LIMIT 1;")
            active_row = cursor.fetchone()
            if not active_row:
                return []
            plan_id = active_row["id"]

        query = "SELECT * FROM sessions WHERE plan_id = ?"
        params: List[Any] = [plan_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY date ASC, id ASC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            {
                "id": r["id"],
                "plan_id": r["plan_id"],
                "date": r["date"],
                "subject": r["subject"],
                "topic": r["topic"],
                "duration_minutes": r["duration_minutes"],
                "status": r["status"],
                "completed_at": r["completed_at"],
                "notes": r["notes"],
            }
            for r in rows
        ]


def get_session_by_id(session_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves a single session by its primary ID."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "plan_id": row["plan_id"],
            "date": row["date"],
            "subject": row["subject"],
            "topic": row["topic"],
            "duration_minutes": row["duration_minutes"],
            "status": row["status"],
            "completed_at": row["completed_at"],
            "notes": row["notes"],
        }


def update_session_status(
    session_id: int,
    status: str,
    notes: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    """Updates session status (Planned or Completed). Sets completed_at when status is Completed."""
    init_db(db_path)
    completed_at = datetime.now().isoformat() if status == "Completed" else None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if notes is not None:
            cursor.execute(
                """
                UPDATE sessions
                SET status = ?, completed_at = ?, notes = ?
                WHERE id = ?;
                """,
                (status, completed_at, notes, session_id),
            )
        else:
            cursor.execute(
                """
                UPDATE sessions
                SET status = ?, completed_at = ?
                WHERE id = ?;
                """,
                (status, completed_at, session_id),
            )
        conn.commit()
        return cursor.rowcount > 0


def replace_planned_sessions(
    plan_id: int,
    new_sessions: List[Dict[str, Any]],
    from_date: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """
    Replaces planned sessions for a plan while strictly preserving completed sessions.
    If from_date is provided, only replaces planned sessions scheduled on or after that date.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        if from_date:
            cursor.execute(
                """
                DELETE FROM sessions
                WHERE plan_id = ? AND status = 'Planned' AND date >= ?;
                """,
                (plan_id, from_date),
            )
        else:
            cursor.execute(
                """
                DELETE FROM sessions
                WHERE plan_id = ? AND status = 'Planned';
                """,
                (plan_id,),
            )

        # Insert new planned sessions
        inserted = 0
        for s in new_sessions:
            cursor.execute(
                """
                INSERT INTO sessions (plan_id, date, subject, topic, duration_minutes, status, notes)
                VALUES (?, ?, ?, ?, ?, 'Planned', ?);
                """,
                (
                    plan_id,
                    s["date"],
                    s["subject"],
                    s["topic"],
                    s["duration_minutes"],
                    s.get("notes", "Replanned session"),
                ),
            )
            inserted += 1

        conn.commit()
        return inserted


def get_study_stats(plan_id: Optional[int] = None, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Calculates comprehensive progress and time stats for the active plan."""
    init_db(db_path)
    sessions = get_sessions(plan_id=plan_id, db_path=db_path)
    today_str = date.today().isoformat()
    seven_days_ago_str = (date.today() - timedelta(days=7)).isoformat()

    total_sessions = len(sessions)
    completed_sessions = [s for s in sessions if s["status"] == "Completed"]
    planned_sessions = [s for s in sessions if s["status"] == "Planned"]

    completed_minutes = sum(s["duration_minutes"] for s in completed_sessions)
    remaining_minutes = sum(s["duration_minutes"] for s in planned_sessions)
    total_minutes = completed_minutes + remaining_minutes

    # Sessions completed in the last 7 days (or this week)
    week_completed = [
        s for s in completed_sessions
        if s.get("completed_at") and s["completed_at"][:10] >= seven_days_ago_str
        or s["date"] >= seven_days_ago_str
    ]
    week_completed_minutes = sum(s["duration_minutes"] for s in week_completed)

    # Today's sessions
    today_sessions = [s for s in sessions if s["date"] == today_str]

    # Missed past sessions (date < today and still planned)
    missed_sessions = [s for s in sessions if s["date"] < today_str and s["status"] == "Planned"]

    completion_percentage = (
        round((len(completed_sessions) / total_sessions) * 100, 1) if total_sessions > 0 else 0.0
    )

    return {
        "total_sessions": total_sessions,
        "completed_count": len(completed_sessions),
        "planned_count": len(planned_sessions),
        "completed_minutes": completed_minutes,
        "remaining_minutes": remaining_minutes,
        "total_minutes": total_minutes,
        "completion_percentage": completion_percentage,
        "week_completed_count": len(week_completed),
        "week_completed_minutes": week_completed_minutes,
        "today_sessions": today_sessions,
        "missed_sessions": missed_sessions,
    }


def clear_all_plans(db_path: str = DEFAULT_DB_PATH) -> None:
    """Clears all plans and sessions (useful for reset)."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM sessions;")
        conn.execute("DELETE FROM topics;")
        conn.execute("DELETE FROM subjects;")
        conn.execute("DELETE FROM plans;")
        conn.commit()
