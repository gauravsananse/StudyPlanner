"""
Study Planner Agent - Streamlit Application
A modern, student-friendly AI-powered study planner with tool-using Gemini agent,
local SQLite persistence, and responsive interactive schedule management.
"""

import os
from datetime import date, timedelta
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv

import agent
import database
import planner

# Load environment variables
load_dotenv()

# Streamlit Page Configuration
st.set_page_config(
    page_title="Study Planner Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database tables
database.init_db()

# Custom Calm & Student-Friendly CSS Styling
st.markdown(
    """
    <style>
    /* Global Styles */
    .main-header {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #1E293B;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        color: #64748B;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    /* Metric Card styling */
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2563EB;
        margin: 0.2rem 0;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    /* Session Card */
    .session-card-planned {
        background-color: #FFFFFF;
        border-left: 5px solid #3B82F6;
        border: 1px solid #E2E8F0;
        border-left-width: 5px;
        border-left-color: #3B82F6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .session-card-completed {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-left-width: 5px;
        border-left-color: #22C55E;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .badge-planned {
        background-color: #EFF6FF;
        color: #1D4ED8;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-completed {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    /* Tool execution pill */
    .tool-badge {
        display: inline-block;
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        color: #334155;
        font-size: 0.75rem;
        border-radius: 12px;
        padding: 0.15rem 0.6rem;
        margin-right: 0.3rem;
        margin-top: 0.3rem;
        font-family: monospace;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# Session State Initialization
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_api_key" not in st.session_state:
    st.session_state.session_api_key = os.getenv("GEMINI_API_KEY", "")
if "selected_model" not in st.session_state:
    st.session_state.selected_model = os.getenv("GEMINI_MODEL", agent.DEFAULT_GEMINI_MODEL)
if "pending_ui_proposal" not in st.session_state:
    st.session_state.pending_ui_proposal = None


# ==========================================
# Sidebar: Setup, Credentials & Plan Summary
# ==========================================
with st.sidebar:
    st.markdown("## 🎓 **Study Planner Agent**")
    st.caption("AI-Assisted Adaptive Exam Preparation")
    st.markdown("---")

    # API Key Configuration
    st.markdown("### 🔑 **Gemini API Key**")
    env_key = os.getenv("GEMINI_API_KEY", "").strip()

    if env_key or st.session_state.session_api_key:
        st.success("API Key configured", icon="✅")
        with st.expander("Update / Change Key"):
            new_key = st.text_input(
                "API Key",
                value=st.session_state.session_api_key or env_key,
                type="password",
                help="Stored only in current browser session or .env file",
            )
            if new_key != st.session_state.session_api_key:
                st.session_state.session_api_key = new_key
                st.rerun()
    else:
        st.warning("API Key not found", icon="⚠️")
        entered_key = st.text_input(
            "Enter Gemini API Key",
            type="password",
            placeholder="AIzaSy...",
            help="Get a free key at https://aistudio.google.com/",
        )
        if entered_key:
            st.session_state.session_api_key = entered_key
            st.success("Key applied for this session!")
            st.rerun()
        st.info("Manual plan creation & schedule tracking work even without an API key.")

    # Model Configuration
    st.markdown("### ⚙️ **Model Selection**")
    model_options = [
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]
    cur_model_idx = (
        model_options.index(st.session_state.selected_model)
        if st.session_state.selected_model in model_options
        else 0
    )
    st.session_state.selected_model = st.selectbox(
        "Gemini Model",
        options=model_options,
        index=cur_model_idx,
        help="gemini-3.8-flash is the latest recommended Flash model.",
    )
    st.caption("ℹ️ *Note: Gemini free-tier rate limits apply. Quotas and model availability may vary.*")

    st.markdown("---")

    # Active Plan Quick Summary
    active_plan = database.get_active_plan()
    if active_plan:
        st.markdown("### 📋 **Current Plan**")
        st.write(f"**Exam Date:** `{active_plan['exam_date']}`")
        try:
            days_left = (date.fromisoformat(active_plan["exam_date"]) - date.today()).days
            st.write(f"**Days to Exam:** `{max(0, days_left)} days`")
        except Exception:
            pass

        stats = database.get_study_stats(plan_id=active_plan["id"])
        st.progress(stats["completion_percentage"] / 100.0)
        st.caption(f"{stats['completion_percentage']}% complete ({stats['completed_count']}/{stats['total_sessions']} sessions)")

        with st.expander("Reset / Clear Plan"):
            st.warning("This will permanently delete the current plan and its sessions.")
            if st.button("Delete Plan", type="secondary", use_container_width=True):
                database.clear_all_plans()
                st.session_state.pending_ui_proposal = None
                st.success("Plan cleared.")
                st.rerun()
    else:
        st.markdown("### 📋 **Current Plan**")
        st.caption("No active plan yet. Go to **Plan Setup** or ask the Agent!")


# ==========================================
# Main App Header & Navigation Tabs
# ==========================================
st.markdown("<h2 class='main-header'>🎯 Study Planner Agent</h2>", unsafe_allow_html=True)
st.markdown(
    "<p class='sub-header'>Your goal-oriented, adaptive study partner with real-time tool calling.</p>",
    unsafe_allow_html=True,
)

tab_schedule, tab_chat, tab_setup, tab_help = st.tabs(
    ["📅 Study Schedule", "🤖 Agent Chat", "⚙️ Plan Setup", "ℹ️ Setup & Help"]
)


# ==========================================
# TAB 1: 📅 Study Schedule
# ==========================================
with tab_schedule:
    plan = database.get_active_plan()

    if not plan:
        st.info("💡 **You don't have an active study plan yet.**", icon="ℹ️")
        col_c1, col_c2 = st.columns([1, 1])
        with col_c1:
            st.markdown(
                """
                Get started in two easy ways:
                1. **Use the Plan Setup tab** to configure subjects, topics, and schedule manually.
                2. **Ask the Agent in Chat** (e.g. *"Create a study plan for Biology and Chemistry before Dec 1st"*).
                """
            )
    else:
        stats = database.get_study_stats(plan_id=plan["id"])

        # Top Metric Cards
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Completed Sessions</div>
                    <div class="metric-value">{stats['completed_count']} <span style="font-size:1rem;color:#64748B">/ {stats['total_sessions']}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Remaining Time</div>
                    <div class="metric-value">{round(stats['remaining_minutes'] / 60, 1)} <span style="font-size:1rem;color:#64748B">hrs</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Studied This Week</div>
                    <div class="metric-value">{stats['week_completed_minutes']} <span style="font-size:1rem;color:#64748B">min</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Overall Progress</div>
                    <div class="metric-value">{stats['completion_percentage']}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Check for missed sessions alert
        if stats["missed_sessions"]:
            st.warning(
                f"⚠️ **You have {len(stats['missed_sessions'])} past session(s) marked as uncompleted.** "
                "You can ask the AI agent to replan or use the Replanning button below.",
                icon="⚠️",
            )
            if st.button("🔄 Propose Automatic Replan for Missed Topics", key="replan_btn_quick"):
                proposal = planner.propose_replan_schedule(
                    plan, database.get_sessions(plan_id=plan["id"])
                )
                st.session_state.pending_ui_proposal = proposal
                st.rerun()

        # Pending Proposal Confirmation Banner (if any)
        if st.session_state.pending_ui_proposal:
            prop = st.session_state.pending_ui_proposal
            st.success(
                f"📋 **Proposed Schedule Ready:** {prop['summary']}\n\n"
                f"Reschedules {prop['new_sessions_count']} remaining sessions starting today while preserving {prop['preserved_completed_count']} completed sessions."
            )
            c_apply, c_cancel = st.columns([1, 1])
            with c_apply:
                if st.button("✅ Confirm & Apply Proposed Schedule", type="primary", use_container_width=True):
                    database.replace_planned_sessions(
                        plan_id=plan["id"],
                        new_sessions=prop["proposed_sessions"],
                        from_date=date.today().isoformat(),
                    )
                    st.session_state.pending_ui_proposal = None
                    st.success("Schedule successfully updated!")
                    st.rerun()
            with c_cancel:
                if st.button("❌ Dismiss Proposal", use_container_width=True):
                    st.session_state.pending_ui_proposal = None
                    st.rerun()

        st.markdown("---")

        # Filters and View Controls
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            filter_choice = st.radio(
                "Filter Sessions:",
                ["All Sessions", "Today's Sessions", "Upcoming (Next 7 Days)", "Planned Only", "Completed Only"],
                horizontal=True,
            )

        all_sessions = database.get_sessions(plan_id=plan["id"])
        today_str = date.today().isoformat()
        next_week_str = (date.today() + timedelta(days=7)).isoformat()

        # Apply filter
        if filter_choice == "Today's Sessions":
            display_sessions = [s for s in all_sessions if s["date"] == today_str]
        elif filter_choice == "Upcoming (Next 7 Days)":
            display_sessions = [s for s in all_sessions if today_str <= s["date"] <= next_week_str]
        elif filter_choice == "Planned Only":
            display_sessions = [s for s in all_sessions if s["status"] == "Planned"]
        elif filter_choice == "Completed Only":
            display_sessions = [s for s in all_sessions if s["status"] == "Completed"]
        else:
            display_sessions = all_sessions

        st.caption(f"Showing **{len(display_sessions)}** of {len(all_sessions)} total sessions.")

        if not display_sessions:
            st.info("No sessions match the selected filter.")
        else:
            for s in display_sessions:
                is_completed = s["status"] == "Completed"
                card_class = "session-card-completed" if is_completed else "session-card-planned"
                badge_class = "badge-completed" if is_completed else "badge-planned"
                badge_text = "Completed" if is_completed else "Planned"

                # Check if session is today or past
                date_tag = ""
                if s["date"] == today_str:
                    date_tag = " <span style='color:#2563EB;font-weight:600;'>[TODAY]</span>"
                elif s["date"] < today_str and not is_completed:
                    date_tag = " <span style='color:#DC2626;font-weight:600;'>[MISSED]</span>"

                # Render Card Row
                col_info, col_btn = st.columns([5, 1])
                with col_info:
                    st.markdown(
                        f"""
                        <div class="{card_class}">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:700; font-size:1.05rem; color:#1E293B;">
                                    📅 {s['date']} {date_tag}
                                </span>
                                <span class="{badge_class}">{badge_text}</span>
                            </div>
                            <div style="margin-top:0.4rem; font-size:0.95rem;">
                                <strong>{s['subject']}</strong>: {s['topic']}
                            </div>
                            <div style="font-size:0.85rem; color:#64748B; margin-top:0.2rem;">
                                ⏱️ {s['duration_minutes']} minutes • <em>{s.get('notes', '')}</em>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    if not is_completed:
                        if st.button("Mark Done ✅", key=f"done_btn_{s['id']}", use_container_width=True):
                            database.update_session_status(s["id"], "Completed")
                            st.rerun()
                    else:
                        st.markdown("<p style='text-align:center;color:#16A34A;font-weight:bold;margin-top:1.2rem;'>Done ✓</p>", unsafe_allow_html=True)


# ==========================================
# TAB 2: 🤖 Agent Chat
# ==========================================
with tab_chat:
    st.markdown("### 💬 **Pair-Programming Study Agent**")
    st.caption("Ask questions, request schedule adjustments, or generate plans using Gemini function calling.")

    # Quick Suggestion Chips
    st.markdown("**Quick prompts:**")
    qc1, qc2, qc3, qc4 = st.columns(4)
    quick_prompt = None
    with qc1:
        if st.button("📅 What should I study today?", use_container_width=True):
            quick_prompt = "What should I study today?"
    with qc2:
        if st.button("⏳ What is still unfinished?", use_container_width=True):
            quick_prompt = "What is still unfinished in my study plan?"
    with qc3:
        if st.button("⏱️ Study time this week?", use_container_width=True):
            quick_prompt = "How much time did I study this week?"
    with qc4:
        if st.button("🔄 Adjust after missed session", use_container_width=True):
            quick_prompt = "I missed a study session. Can you propose an updated schedule for my remaining topics?"

    # Check for pending agent proposal or new plan awaiting user confirmation
    pending_prop = agent.get_pending_proposal()
    pending_new = agent.get_pending_new_plan()

    if pending_prop:
        st.info("🔔 **The AI Agent proposed a replan!** Review the proposal and confirm to commit to your database.")
        col_cp1, col_cp2 = st.columns([1, 1])
        with col_cp1:
            if st.button("✅ Confirm & Save Replan Now", type="primary", use_container_width=True):
                ok, msg = agent.confirm_pending_proposal_manually()
                if ok:
                    st.success(msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": f"Confirmed! {msg}"}
                    )
                    st.rerun()
                else:
                    st.error(msg)
        with col_cp2:
            if st.button("❌ Reject Replan", use_container_width=True):
                agent._PENDING_PROPOSAL = None
                st.session_state.messages.append(
                    {"role": "user", "content": "I reject this proposed replan. Keep my current schedule."}
                )
                st.rerun()

    if pending_new:
        st.info("🔔 **The AI Agent generated a new study plan proposal!** Confirm below to save it.")
        col_cn1, col_cn2 = st.columns([1, 1])
        with col_cn1:
            if st.button("✅ Confirm & Save New Plan", type="primary", use_container_width=True):
                ok, msg = agent.confirm_pending_new_plan_manually()
                if ok:
                    st.success(msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": f"Confirmed! {msg}"}
                    )
                    st.rerun()
                else:
                    st.error(msg)
        with col_cn2:
            if st.button("❌ Reject Plan", use_container_width=True):
                agent._PENDING_NEW_PLAN = None
                st.session_state.messages.append(
                    {"role": "user", "content": "I don't want to save this proposed plan."}
                )
                st.rerun()

    st.markdown("---")

    # Display Chat History
    for msg in st.session_state.messages:
        role = msg.get("role", "user")
        with st.chat_message(role):
            st.markdown(msg.get("content", ""))
            if msg.get("tools_used"):
                tools_html = "".join(
                    f"<span class='tool-badge'>🔧 Tool: {t['tool']}</span>"
                    for t in msg["tools_used"]
                )
                st.markdown(tools_html, unsafe_allow_html=True)

    # Chat Input Box
    user_input = st.chat_input("Ask a question or request a plan adjustment...")
    prompt_to_send = quick_prompt or user_input

    if prompt_to_send:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt_to_send})
        with st.chat_message("user"):
            st.markdown(prompt_to_send)

        # Call AI Agent
        with st.chat_message("assistant"):
            with st.spinner("Agent is reasoning and consulting the study database..."):
                active_key = st.session_state.session_api_key or os.getenv("GEMINI_API_KEY", "")
                result = agent.run_agent_turn(
                    user_message=prompt_to_send,
                    conversation_history=st.session_state.messages[:-1],
                    api_key=active_key,
                    model_name=st.session_state.selected_model,
                )

                st.markdown(result["response"])

                if result.get("tools_used"):
                    tools_html = "".join(
                        f"<span class='tool-badge'>🔧 Tool: {t['tool']}</span>"
                        for t in result["tools_used"]
                    )
                    st.markdown(tools_html, unsafe_allow_html=True)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"],
                    "tools_used": result.get("tools_used", []),
                })

        st.rerun()

    # Clear chat button
    if st.session_state.messages:
        if st.button("🧹 Clear Conversation History", type="secondary"):
            st.session_state.messages = []
            st.rerun()


# ==========================================
# TAB 3: ⚙️ Plan Setup
# ==========================================
with tab_setup:
    st.markdown("### 📋 **Configure Your Study Plan**")
    st.caption("Set up your upcoming exam, subjects, and study availability.")

    with st.form("plan_setup_form"):
        # 1. Exam Date
        default_exam_date = date.today() + timedelta(days=30)
        exam_date_val = st.date_input(
            "Exam Date",
            value=default_exam_date,
            min_value=date.today() + timedelta(days=1),
            help="Your target examination date. Must be in the future.",
        )

        st.markdown("#### **Subjects and Topics**")
        st.caption("Enter subjects and comma-separated topics for each.")

        # Up to 4 subjects in the beginner-friendly setup form
        c_s1, c_t1 = st.columns([1, 2])
        with c_s1:
            subj1 = st.text_input("Subject 1", value="Mathematics", placeholder="e.g. Mathematics")
        with c_t1:
            top1 = st.text_input(
                "Topics for Subject 1 (comma-separated)",
                value="Calculus, Linear Algebra, Probability, Statistics",
                placeholder="Topic A, Topic B, Topic C",
            )

        c_s2, c_t2 = st.columns([1, 2])
        with c_s2:
            subj2 = st.text_input("Subject 2 (optional)", value="Physics", placeholder="e.g. Physics")
        with c_t2:
            top2 = st.text_input(
                "Topics for Subject 2",
                value="Mechanics, Thermodynamics, Electromagnetism",
                placeholder="Topic X, Topic Y",
            )

        c_s3, c_t3 = st.columns([1, 2])
        with c_s3:
            subj3 = st.text_input("Subject 3 (optional)", placeholder="e.g. Computer Science")
        with c_t3:
            top3 = st.text_input("Topics for Subject 3", placeholder="Data Structures, Algorithms")

        st.markdown("#### **Availability & Schedule Settings**")
        c_av1, c_av2 = st.columns([2, 1])

        with c_av1:
            study_days = st.multiselect(
                "Available Study Days",
                options=planner.VALID_WEEKDAYS,
                default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                help="Days of the week you can dedicate to studying.",
            )

        with c_av2:
            daily_minutes = st.number_input(
                "Daily Study Minutes",
                min_value=15,
                max_value=480,
                value=60,
                step=15,
                help="How many minutes you plan to study on each available day.",
            )

        rest_days = st.multiselect(
            "Optional Designated Rest Days",
            options=planner.VALID_WEEKDAYS,
            default=["Sunday"],
            help="Weekly rest days where no sessions will be scheduled.",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_submit = st.form_submit_button("🚀 Generate & Save Study Plan", type="primary")

    if btn_submit:
        # Build subjects dictionary
        subjects_dict: Dict[str, List[str]] = {}
        for s, t in [(subj1, top1), (subj2, top2), (subj3, top3)]:
            s_clean = s.strip()
            if s_clean and t.strip():
                t_list = [item.strip() for item in t.split(",") if item.strip()]
                if t_list:
                    subjects_dict[s_clean] = t_list

        # Validate inputs
        is_valid, err_msg, sanitized = planner.validate_plan_inputs(
            exam_date_str=exam_date_val.isoformat(),
            subjects_dict=subjects_dict,
            available_days=study_days,
            daily_minutes=daily_minutes,
            rest_days=rest_days,
        )

        if not is_valid:
            st.error(f"❌ {err_msg}")
        else:
            # Generate schedule
            sessions = planner.generate_schedule(
                exam_date_str=sanitized["exam_date"],
                subjects_dict=sanitized["subjects"],
                available_days=sanitized["available_days"],
                daily_minutes=sanitized["daily_minutes"],
                rest_days=sanitized["rest_days"],
            )

            # Save to SQLite
            plan_id = database.save_plan(
                exam_date=sanitized["exam_date"],
                subjects_dict=sanitized["subjects"],
                available_days=sanitized["available_days"],
                daily_minutes=sanitized["daily_minutes"],
                rest_days=sanitized["rest_days"],
                sessions=sessions,
            )

            st.success(
                f"🎉 **Plan successfully created and saved!** (#{plan_id}) "
                f"Scheduled {len(sessions)} sessions until {sanitized['exam_date']}."
            )
            # Switch view to Study Schedule
            st.session_state.pending_ui_proposal = None
            st.rerun()


# ==========================================
# TAB 4: ℹ️ Setup & Help
# ==========================================
with tab_help:
    st.markdown("### 🛠️ **System Setup, Tools & Help Guide**")

    # API Key Setup Guide
    with st.expander("🔑 How to Get and Configure your Gemini API Key", expanded=not bool(st.session_state.session_api_key)):
        st.markdown(
            """
            1. **Get a free Gemini API key**:
               - Visit Google AI Studio: [https://aistudio.google.com/](https://aistudio.google.com/)
               - Sign in with your Google Account and click **Get API key**.
               - Create a key in a few seconds.

            2. **Set the Key in this App**:
               - **Option A (Quick UI Input)**: Paste your key in the sidebar of this app under **Gemini API Key**.
               - **Option B (Permanent .env file)**: Open the `.env` file in the project folder and set:
                 ```bash
                 GEMINI_API_KEY="your_actual_api_key_here"
                 GEMINI_MODEL="gemini-2.5-flash"
                 ```

            3. **Free Tier & Model Notes**:
               - `gemini-2.5-flash` and `gemini-2.0-flash` provide free-tier access with generous rate limits.
               - Free tier quotas and model availability are subject to Google AI Studio policies.
               - If you experience rate limits, the app catches the error cleanly and offers fallback options.
            """
        )

    # Agent Tools Documentation
    with st.expander("🤖 How the Agent Tools Work (Under the Hood)", expanded=True):
        st.markdown(
            """
            This app uses the official Google GenAI SDK for **function calling**:

            | Tool Name | Action | Safety & Confirmation |
            | :--- | :--- | :--- |
            | `get_plan` | Reads current plan, today's tasks, stats, and unfinished topics from SQLite. | Read-only. Never guesses facts. |
            | `create_plan` | Validates exam date, study minutes, and schedule. Generates timetable. | Proposes plan first; saves only after confirmation. |
            | `mark_session_complete` | Marks one specific session ID as completed in SQLite. | Requires explicit student intent. |
            | `propose_replan` | Re-allocates unfinished topics across remaining days after missed sessions. | Read-only calculation. Does not touch DB. |
            | `save_replan` | Replaces future planned sessions while preserving completed sessions. | Requires explicit confirmation (`confirmed=True`). |

            The Python application (not the model) validates all dates, daily limits, and database operations.
            """
        )

    # Windows PowerShell Run Commands
    with st.expander("💻 Windows PowerShell Setup and Run Commands"):
        st.markdown(
            """
            Run these commands in Windows PowerShell:

            ```powershell
            # 1. Open the project folder
            cd "c:\\Users\\gaura\\Downloads\\AI Based Study Planner"

            # 2. Activate the virtual environment
            .\\.venv\\Scripts\\Activate.ps1

            # 3. Start the Streamlit application
            streamlit run app.py
            ```
            """
        )
