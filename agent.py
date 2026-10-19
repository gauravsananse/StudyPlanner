"""
Agent module for Study Planner Agent.
Integrates with Google's supported Gen AI Python SDK (google-genai) for Gemini function calling.
Validates model requests, executes strictly bounded tool calling, and provides safe database operations.
"""

import os
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

import database
import planner

# Module-level store for proposals awaiting user confirmation
_PENDING_PROPOSAL: Optional[Dict[str, Any]] = None
_PENDING_NEW_PLAN: Optional[Dict[str, Any]] = None

SYSTEM_INSTRUCTION = """You are a careful, student-friendly AI study planning assistant.
Your goal is to help the student organize, manage, track, and adapt their study schedule for exams.

Strict Behavioral Rules:
1. Use the application tools (`get_plan`, `create_plan`, `mark_session_complete`, `propose_replan`, `save_replan`) as your ONLY source of truth for saved plans, schedules, and progress.
2. Never invent, guess, or assume dates, subjects, topics, completed hours, or availability.
3. Propose plans or changes to the student first. NEVER save a new plan or replan without asking for user confirmation (`confirmed=False` initially). Only call `save_replan(confirmed=True)` or `create_plan(..., confirmed=True)` after the student explicitly confirms.
4. Never claim an action succeeded (such as saving a plan, updating sessions, or marking work complete) until the application tool returns a confirmation that the database operation succeeded.
5. Never mark a session complete unless the student explicitly asks to complete that specific session. Always verify the session ID from `get_plan`.
6. When answering questions like 'What should I study today?', 'What is still unfinished?', or 'How much time did I study this week?', call `get_plan` first and answer accurately based on the returned data.
7. If there is no active plan yet, guide the student with friendly instructions on what information is needed (exam date, subjects, topics, available days, minutes per day).
8. Keep responses clear, motivating, and well-structured with bullet points and bold text where helpful.
"""

# Default recommended model for Gemini (fast, capable, free-tier eligible)
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


# ==========================================
# Tool Implementations (Application Functions)
# ==========================================

def get_plan() -> Dict[str, Any]:
    """Reads the current active study plan and sessions from the SQLite database.
    Returns structured data including completion status, stats, and today's schedule.
    """
    plan = database.get_active_plan()
    if not plan:
        return {
            "has_active_plan": False,
            "message": "No active study plan exists yet. Please set up a plan first.",
        }

    sessions = database.get_sessions(plan_id=plan["id"])
    stats = database.get_study_stats(plan_id=plan["id"])
    today_str = date.today().isoformat()

    # Identify unfinished topics
    completed_topics = {
        (s["subject"], s["topic"].replace("Review & Practice: ", ""))
        for s in sessions
        if s["status"] == "Completed"
    }

    all_topics = []
    for subj in plan.get("subjects", []):
        for top in subj.get("topics", []):
            all_topics.append({"subject": subj["name"], "topic": top})

    unfinished_topics = [
        t for t in all_topics if (t["subject"], t["topic"]) not in completed_topics
    ]

    return {
        "has_active_plan": True,
        "plan_details": {
            "id": plan["id"],
            "title": plan["title"],
            "exam_date": plan["exam_date"],
            "available_days": plan["available_days"],
            "daily_minutes": plan["daily_minutes"],
            "rest_days": plan.get("rest_days", []),
            "created_at": plan["created_at"],
        },
        "stats": {
            "total_sessions": stats["total_sessions"],
            "completed_sessions": stats["completed_count"],
            "planned_sessions": stats["planned_count"],
            "completed_minutes": stats["completed_minutes"],
            "remaining_minutes": stats["remaining_minutes"],
            "total_minutes": stats["total_minutes"],
            "completion_percentage": stats["completion_percentage"],
            "week_completed_minutes": stats["week_completed_minutes"],
            "week_completed_count": stats["week_completed_count"],
        },
        "today_sessions": [
            {
                "id": s["id"],
                "subject": s["subject"],
                "topic": s["topic"],
                "duration_minutes": s["duration_minutes"],
                "status": s["status"],
            }
            for s in sessions
            if s["date"] == today_str
        ],
        "unfinished_topics": unfinished_topics,
        "recent_sessions_sample": [
            {
                "id": s["id"],
                "date": s["date"],
                "subject": s["subject"],
                "topic": s["topic"],
                "duration_minutes": s["duration_minutes"],
                "status": s["status"],
            }
            for s in sessions[:10]
        ],
    }


def create_plan(
    exam_date: str,
    subjects_and_topics: Dict[str, List[str]],
    available_days: List[str],
    daily_minutes: int,
    rest_days: Optional[List[str]] = None,
    confirmed: bool = False,
) -> Dict[str, Any]:
    """Generates and optionally saves a new study plan.
    Validates exam date, topics, and study minutes.
    If confirmed is False, returns a proposed schedule for student confirmation.
    If confirmed is True, saves the plan to SQLite and returns confirmation.
    """
    global _PENDING_NEW_PLAN
    is_valid, err_msg, sanitized = planner.validate_plan_inputs(
        exam_date_str=exam_date,
        subjects_dict=subjects_and_topics,
        available_days=available_days,
        daily_minutes=daily_minutes,
        rest_days=rest_days,
    )

    if not is_valid:
        return {"success": False, "error": f"Validation Error: {err_msg}"}

    # Generate timetable
    proposed_sessions = planner.generate_schedule(
        exam_date_str=sanitized["exam_date"],
        subjects_dict=sanitized["subjects"],
        available_days=sanitized["available_days"],
        daily_minutes=sanitized["daily_minutes"],
        rest_days=sanitized["rest_days"],
    )

    if not confirmed:
        _PENDING_NEW_PLAN = {
            "sanitized": sanitized,
            "sessions": proposed_sessions,
        }
        return {
            "success": True,
            "requires_user_confirmation": True,
            "message": (
                f"Proposed a plan with {len(proposed_sessions)} sessions from today until {sanitized['exam_date']}. "
                "Please present this proposed outline to the student and ask if they would like to confirm and save it."
            ),
            "summary": {
                "exam_date": sanitized["exam_date"],
                "total_sessions": len(proposed_sessions),
                "daily_minutes": sanitized["daily_minutes"],
                "study_days": sanitized["available_days"],
                "rest_days": sanitized["rest_days"],
            },
            "sample_sessions": proposed_sessions[:6],
        }

    # User confirmed! Save to database
    plan_id = database.save_plan(
        exam_date=sanitized["exam_date"],
        subjects_dict=sanitized["subjects"],
        available_days=sanitized["available_days"],
        daily_minutes=sanitized["daily_minutes"],
        rest_days=sanitized["rest_days"],
        sessions=proposed_sessions,
    )
    _PENDING_NEW_PLAN = None

    return {
        "success": True,
        "saved": True,
        "plan_id": plan_id,
        "total_sessions": len(proposed_sessions),
        "message": f"Successfully created and saved your study plan (#{plan_id}) with {len(proposed_sessions)} sessions to SQLite.",
    }


def mark_session_complete(session_id: int) -> Dict[str, Any]:
    """Marks one existing planned study session as completed in SQLite.
    Requires a valid session ID. Only updates planned sessions.
    """
    try:
        s_id = int(session_id)
    except (ValueError, TypeError):
        return {"success": False, "error": f"Invalid session ID: '{session_id}'. Must be an integer."}

    session = database.get_session_by_id(s_id)
    if not session:
        return {"success": False, "error": f"No session found with ID {s_id}."}

    if session["status"] == "Completed":
        return {
            "success": True,
            "already_completed": True,
            "message": f"Session #{s_id} ('{session['topic']}' in {session['subject']}) is already marked Completed.",
        }

    updated = database.update_session_status(s_id, status="Completed")
    if updated:
        return {
            "success": True,
            "message": f"Session #{s_id} ('{session['topic']}' - {session['subject']} on {session['date']}) is now marked Completed!",
            "session": session,
        }
    return {"success": False, "error": "Database update failed."}


def propose_replan(reason: str = "Missed sessions or changed availability") -> Dict[str, Any]:
    """Reads the current active plan and calculates a proposed schedule for unfinished topics.
    Does NOT save to the database. Returns the proposal for student review.
    """
    global _PENDING_PROPOSAL
    plan = database.get_active_plan()
    if not plan:
        return {"success": False, "error": "No active study plan found to replan."}

    sessions = database.get_sessions(plan_id=plan["id"])
    proposal = planner.propose_replan_schedule(plan_data=plan, existing_sessions=sessions)

    _PENDING_PROPOSAL = {
        "plan_id": plan["id"],
        "proposed_sessions": proposal["proposed_sessions"],
        "summary": proposal["summary"],
    }

    return {
        "success": True,
        "requires_user_confirmation": True,
        "summary": proposal["summary"],
        "preserved_completed_count": proposal["preserved_completed_count"],
        "new_sessions_count": proposal["new_sessions_count"],
        "sample_sessions": proposal["proposed_sessions"][:6],
        "message": (
            "Replanning proposal ready. Show the student the new session count and ask for their confirmation before calling save_replan."
        ),
    }


def save_replan(confirmed: bool = False) -> Dict[str, Any]:
    """Saves the previously proposed replan into the database.
    Requires confirmed=True. Preserves all completed sessions and replaces future planned sessions.
    """
    global _PENDING_PROPOSAL
    if not confirmed:
        return {
            "success": False,
            "error": "Confirmation required: cannot save replan unless the student has explicitly confirmed.",
        }

    plan = database.get_active_plan()
    if not plan:
        return {"success": False, "error": "No active plan found."}

    proposed_sessions = None
    if _PENDING_PROPOSAL and _PENDING_PROPOSAL.get("plan_id") == plan["id"]:
        proposed_sessions = _PENDING_PROPOSAL.get("proposed_sessions")

    if not proposed_sessions:
        # Generate fresh proposal on the fly if needed
        existing = database.get_sessions(plan_id=plan["id"])
        proposal = planner.propose_replan_schedule(plan, existing)
        proposed_sessions = proposal["proposed_sessions"]

    today_str = date.today().isoformat()
    inserted_count = database.replace_planned_sessions(
        plan_id=plan["id"],
        new_sessions=proposed_sessions,
        from_date=today_str,
    )

    _PENDING_PROPOSAL = None

    return {
        "success": True,
        "saved": True,
        "message": f"Successfully updated your schedule! Preserved completed work and scheduled {inserted_count} updated sessions starting from today.",
        "rescheduled_count": inserted_count,
    }


# Map of available tool functions for validation and execution
TOOL_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "get_plan": get_plan,
    "create_plan": create_plan,
    "mark_session_complete": mark_session_complete,
    "propose_replan": propose_replan,
    "save_replan": save_replan,
}


def get_pending_proposal() -> Optional[Dict[str, Any]]:
    """Helper to inspect current pending proposal for the UI."""
    return _PENDING_PROPOSAL


def get_pending_new_plan() -> Optional[Dict[str, Any]]:
    """Helper to inspect current pending new plan for the UI."""
    return _PENDING_NEW_PLAN


def confirm_pending_proposal_manually() -> Tuple[bool, str]:
    """Allows one-click confirmation directly from the Streamlit UI."""
    result = save_replan(confirmed=True)
    if result.get("success"):
        return True, result.get("message", "Schedule updated.")
    return False, result.get("error", "Failed to update schedule.")


def confirm_pending_new_plan_manually() -> Tuple[bool, str]:
    """Allows one-click confirmation of a new plan directly from the Streamlit UI."""
    global _PENDING_NEW_PLAN
    if not _PENDING_NEW_PLAN:
        return False, "No pending plan to confirm."

    sanitized = _PENDING_NEW_PLAN["sanitized"]
    sessions = _PENDING_NEW_PLAN["sessions"]
    plan_id = database.save_plan(
        exam_date=sanitized["exam_date"],
        subjects_dict=sanitized["subjects"],
        available_days=sanitized["available_days"],
        daily_minutes=sanitized["daily_minutes"],
        rest_days=sanitized["rest_days"],
        sessions=sessions,
    )
    _PENDING_NEW_PLAN = None
    return True, f"Plan #{plan_id} saved successfully with {len(sessions)} sessions."


# ==========================================
# Gemini Agent Execution Engine
# ==========================================

def run_agent_turn(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a single conversational turn with Gemini using function calling.
    - Sends user message and history
    - Bounded loop (up to 5 turns) for handling requested tool calls
    - Validates tool names and arguments
    - Returns assistant response, list of tools executed, and status.
    """
    from dotenv import load_dotenv
    load_dotenv()

    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    if not resolved_key or not resolved_key.strip():
        return {
            "success": False,
            "response": (
                "⚠️ **Gemini API Key Missing**\n\n"
                "I cannot process AI requests until a valid Gemini API key is configured.\n"
                "You can add your key in the sidebar, or set `GEMINI_API_KEY` in your `.env` file.\n\n"
                "*(Note: You can still use the **Plan Setup** tab to create schedules, view your plan, "
                "and mark sessions complete manually!)*"
            ),
            "tools_used": [],
            "error_type": "MISSING_KEY",
        }

    resolved_model = model_name or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL

    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError
    except ImportError as e:
        return {
            "success": False,
            "response": f"Failed to import Google GenAI SDK: {str(e)}",
            "tools_used": [],
            "error_type": "SDK_IMPORT_ERROR",
        }

    try:
        client = genai.Client(api_key=resolved_key.strip())

        # Expose tools to Gemini
        tool_callables = [
            get_plan,
            create_plan,
            mark_session_complete,
            propose_replan,
            save_replan,
        ]

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=tool_callables,
            # Disable automatic execution so our Python application validates and controls execution
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2,
        )

        # Build conversation contents from history
        contents: List[types.Content] = []
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.get("content", ""))],
                )
            )

        # Append current user message
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)],
            )
        )

        tools_used: List[Dict[str, Any]] = []
        max_tool_iterations = 5
        iteration = 0
        final_text = ""

        while iteration < max_tool_iterations:
            iteration += 1

            response = client.models.generate_content(
                model=resolved_model,
                contents=contents,
                config=config,
            )

            # Check if candidates exist
            if not response.candidates or not response.candidates[0].content:
                final_text = "I received an empty response. Please try again."
                break

            candidate_content = response.candidates[0].content

            # Check if model requested function calls
            function_calls = response.function_calls

            if function_calls:
                # Append the model's tool call turn to conversation contents
                contents.append(candidate_content)

                # Process each tool call requested by Gemini
                for call in function_calls:
                    fn_name = call.name
                    fn_args = dict(call.args) if call.args else {}

                    # 1. Validate tool name
                    if fn_name not in TOOL_FUNCTIONS:
                        tool_result = {
                            "success": False,
                            "error": f"Tool '{fn_name}' is not recognized or not permitted.",
                        }
                    else:
                        # 2. Execute application function safely
                        fn_func = TOOL_FUNCTIONS[fn_name]
                        try:
                            tool_result = fn_func(**fn_args)
                        except TypeError as te:
                            tool_result = {
                                "success": False,
                                "error": f"Invalid arguments provided to '{fn_name}': {str(te)}",
                            }
                        except Exception as ex:
                            tool_result = {
                                "success": False,
                                "error": f"Execution error in '{fn_name}': {str(ex)}",
                            }

                    tools_used.append({"tool": fn_name, "args": fn_args, "result": tool_result})

                    # 3. Create function response part and append to contents
                    resp_part = types.Part.from_function_response(
                        name=fn_name,
                        response={"result": tool_result},
                    )
                    contents.append(types.Content(role="user", parts=[resp_part]))

                # Loop continues back to model with tool response
                continue

            else:
                # No more tool calls; extract the model's natural language text
                if candidate_content.parts:
                    final_text = "".join(
                        part.text for part in candidate_content.parts if getattr(part, "text", None)
                    )
                else:
                    final_text = response.text or ""
                break

        if not final_text and not tools_used:
            final_text = "I processed your request, but have no additional text to display."

        return {
            "success": True,
            "response": final_text,
            "tools_used": tools_used,
            "error_type": None,
        }

    except Exception as e:
        err_str = str(e)
        if "403" in err_str or "API_KEY_INVALID" in err_str or "Forbidden" in err_str:
            friendly_msg = (
                "❌ **Invalid Gemini API Key**: The API key provided was rejected. "
                "Please verify your key in Google AI Studio and update it in `.env` or the sidebar."
            )
            err_type = "AUTH_ERROR"
        elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            friendly_msg = (
                "⏳ **Gemini Rate Limit / Quota Exceeded**: The Gemini API free-tier quota has been reached. "
                "Please wait a minute or select a different Gemini model in the sidebar."
            )
            err_type = "RATE_LIMIT"
        elif "404" in err_str or "NOT_FOUND" in err_str:
            friendly_msg = (
                f"⚠️ **Model Not Found**: The model `{resolved_model}` was not found. "
                "Try selecting `gemini-2.0-flash` or `gemini-1.5-flash` in the sidebar or check your GEMINI_MODEL setting."
            )
            err_type = "MODEL_NOT_FOUND"
        else:
            friendly_msg = f"⚠️ **Agent Error**: {err_str}"
            err_type = "GENERAL_ERROR"

        return {
            "success": False,
            "response": friendly_msg,
            "tools_used": [],
            "error_type": err_type,
        }
