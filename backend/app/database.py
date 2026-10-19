"""
Database module for Study Planner AI backend.
Manages SQLite connection, foreign keys, and table schemas.
"""

import sqlite3
from typing import Any, Dict, List, Optional
from .config import DATABASE_PATH


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # Plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                daily_hours REAL NOT NULL DEFAULT 2.0,
                preferred_slots TEXT DEFAULT '[]',
                study_days TEXT DEFAULT '["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]',
                unavailable_weeks TEXT DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'Active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # Migrations
        try:
            cursor.execute("ALTER TABLE plans ADD COLUMN study_days TEXT DEFAULT '[\"Monday\",\"Tuesday\",\"Wednesday\",\"Thursday\",\"Friday\",\"Saturday\"]';")
        except Exception:
            pass

        try:
            cursor.execute("ALTER TABLE plans ADD COLUMN unavailable_weeks TEXT DEFAULT '[]';")
        except Exception:
            pass



        # Subjects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                topics TEXT NOT NULL, -- JSON array of topics
                FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE
            );
        """)

        # Dynamic Sessions table with concrete time slots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                actionable_task TEXT,
                status TEXT NOT NULL DEFAULT 'Planned',
                completed_at TEXT,
                notes TEXT,
                FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # Goals table for dashboard goal-tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                target_hours REAL NOT NULL DEFAULT 10.0,
                achieved_hours REAL NOT NULL DEFAULT 0.0,
                is_completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        conn.commit()
