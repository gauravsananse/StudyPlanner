import React, { useState, useEffect } from "react";
import { 
  Clock, CheckCircle, Calendar, Target, Flame, 
  ArrowRight, Sparkles, Check, Plus, AlertCircle,
  Bell, RefreshCw, AlertTriangle
} from "lucide-react";
import { 
  fetchDashboardData, 
  toggleSessionStatus, 
  createGoal, 
  toggleGoal,
  rescheduleMissedSessions,
  markSessionMissed
} from "../api";
import { playStudyAlertSequence } from "../utils/alarmSound";
import { requestNotificationPermission, showSystemNotification } from "../utils/alarmManager";

export default function Dashboard({ onOpenNewPlan, onViewSchedule }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newGoalTitle, setNewGoalTitle] = useState("");
  const [newGoalHours, setNewGoalHours] = useState(10);
  const [showGoalInput, setShowGoalInput] = useState(false);
  const [reschedulingPlanId, setReschedulingPlanId] = useState(null);
  const [rescheduleNotice, setRescheduleNotice] = useState("");

  const loadData = async () => {
    try {
      const res = await fetchDashboardData();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleSession = async (sessionId) => {
    try {
      await toggleSessionStatus(sessionId);
      loadData();
    } catch (err) {
      alert("Failed to update session: " + err.message);
    }
  };

  const handleMarkMissed = async (sessionId, planId) => {
    if (!confirm("Mark this session as missed? You can reschedule it across remaining days before the exam.")) return;
    try {
      await markSessionMissed(sessionId);
      await handleReschedule(planId);
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  const handleReschedule = async (planId) => {
    if (!planId) return;
    setReschedulingPlanId(planId);
    setRescheduleNotice("");
    try {
      const res = await rescheduleMissedSessions(planId);
      setRescheduleNotice(`✅ ${res.message}`);
      await loadData();
    } catch (err) {
      alert("Rescheduling failed: " + err.message);
    } finally {
      setReschedulingPlanId(null);
    }
  };

  const handleTestAlarm = async () => {
    await requestNotificationPermission();
    playStudyAlertSequence();
    showSystemNotification(
      "🎓 Study Planner Alarm Test",
      "Your study reminder sound and notifications are active and ready!"
    );
  };


  const handleAddGoal = async (e) => {
    e.preventDefault();
    if (!newGoalTitle.trim()) return;
    try {
      await createGoal(newGoalTitle, parseFloat(newGoalHours) || 10);
      setNewGoalTitle("");
      setShowGoalInput(false);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleToggleGoal = async (goalId) => {
    try {
      await toggleGoal(goalId);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  if (loading) {
    return (
      <div className="center-container">
        <div className="spinner"></div>
        <p>Loading your study dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="center-container error-state">
        <AlertCircle size={40} color="#EF4444" />
        <h3>Unable to load dashboard</h3>
        <p>{error}</p>
        <button className="primary-btn" onClick={loadData}>Retry</button>
      </div>
    );
  }

  const { metrics, today_sessions, upcoming_exams, goals, user } = data;

  return (
    <div className="dashboard-content">
      {/* Welcome Banner */}
      <div className="welcome-banner">
        <div className="welcome-text">
          <h1>Welcome back, {user?.name}! 🎓</h1>
          <p>
            You have <strong>{today_sessions.length}</strong> study sessions scheduled for today. Keep up your momentum!
          </p>
        </div>
        <div className="banner-btn-group">
          <button className="secondary-btn alarm-test-btn" onClick={handleTestAlarm} title="Test study alarm sound & notification">
            <Bell size={18} />
            <span>Test Alarm</span>
          </button>
          <button className="primary-btn pulse-glow" onClick={onOpenNewPlan}>
            <Sparkles size={18} />
            <span>Generate New AI Plan</span>
          </button>
        </div>
      </div>

      {/* Reschedule Success Notice */}
      {rescheduleNotice && (
        <div className="success-banner">
          <span>{rescheduleNotice}</span>
          <button className="close-notice-btn" onClick={() => setRescheduleNotice("")}>✕</button>
        </div>
      )}

      {/* Missed Sessions Alert Banner */}
      {data.missed_sessions && data.missed_sessions.length > 0 && (
        <div className="missed-alert-banner">
          <div className="missed-alert-content">
            <div className="missed-alert-icon">
              <AlertTriangle size={24} color="#EF4444" />
            </div>
            <div>
              <h4>⚠️ {data.missed_sessions.length} Missed Study Session{data.missed_sessions.length > 1 ? "s" : ""} Detected</h4>
              <p>
                Life happens! Don't let missed sessions derail your preparation. Click below to automatically redistribute all unfinished topics across your remaining days up until your exam.
              </p>
            </div>
          </div>
          <button 
            className="primary-btn reschedule-banner-btn"
            onClick={() => handleReschedule(data.missed_sessions[0].plan_id)}
            disabled={reschedulingPlanId !== null}
          >
            <RefreshCw size={16} className={reschedulingPlanId ? "spin" : ""} />
            <span>{reschedulingPlanId ? "Rescheduling..." : "⚡ Reschedule Across Remaining Days"}</span>
          </button>
        </div>
      )}

      {/* Metric Cards Row */}
      <div className="metrics-grid">
        <div className="metric-box">
          <div className="metric-icon-wrap blue">
            <Clock size={22} color="#2563EB" />
          </div>
          <div>
            <div className="metric-num">{metrics.completed_hours} <span className="metric-sub">/ {metrics.total_hours} hrs</span></div>
            <div className="metric-title">Study Time Completed</div>
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-icon-wrap green">
            <CheckCircle size={22} color="#16A34A" />
          </div>
          <div>
            <div className="metric-num">{metrics.completed_sessions} <span className="metric-sub">/ {metrics.total_sessions}</span></div>
            <div className="metric-title">Sessions Completed</div>
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-icon-wrap amber">
            <Calendar size={22} color="#D97706" />
          </div>
          <div>
            <div className="metric-num">{upcoming_exams.length}</div>
            <div className="metric-title">Active Exam Plans</div>
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-icon-wrap purple">
            <Flame size={22} color="#9333EA" />
          </div>
          <div>
            <div className="metric-num">{metrics.completion_rate}%</div>
            <div className="metric-title">Preparation Progress</div>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="dashboard-columns">
        {/* Left Column: Today's Dynamic Time Slots */}
        <div className="dashboard-left">
          <div className="section-header">
            <div>
              <h2>📅 Today's Dynamic Study Slots</h2>
              <p className="section-sub">Actionable tasks broken down into designated study windows with active alarms</p>
            </div>
          </div>

          {today_sessions.length === 0 ? (
            <div className="empty-card">
              <Calendar size={36} color="#94A3B8" />
              <h4>No sessions scheduled for today!</h4>
              <p>Take time to review notes or create a new AI study plan.</p>
              <button className="secondary-btn" onClick={onOpenNewPlan}>
                Create Plan Now
              </button>
            </div>
          ) : (
            <div className="sessions-list">
              {today_sessions.map((sess) => {
                const isCompleted = sess.status === "Completed";
                const isMissed = sess.status === "Missed";
                return (
                  <div key={sess.id} className={`slot-card ${isCompleted ? "completed" : isMissed ? "missed" : ""}`}>
                    <div className="slot-time-badge">
                      <Clock size={14} />
                      <span>{sess.time_slot}</span>
                    </div>

                    <div className="slot-body">
                      <div className="slot-heading">
                        <span className="slot-subject">{sess.subject}</span>
                        <h4 className="slot-topic">{sess.topic}</h4>
                      </div>

                      {sess.actionable_task && (
                        <p className="slot-task">🎯 <strong>Action:</strong> {sess.actionable_task}</p>
                      )}

                      <div className="slot-footer">
                        <span className="slot-duration">⏱️ {sess.duration_minutes} mins</span>
                        {isMissed && <span className="status-badge-missed">Missed</span>}
                      </div>
                    </div>

                    <div className="slot-card-actions">
                      {!isCompleted && (
                        <button
                          className="slot-miss-btn"
                          onClick={() => handleMarkMissed(sess.id, sess.plan_id)}
                          title="Missed this session? Reschedule across remaining days"
                        >
                          <RefreshCw size={13} />
                          <span>Reschedule</span>
                        </button>
                      )}
                      <button
                        className={`check-btn ${isCompleted ? "checked" : ""}`}
                        onClick={() => handleToggleSession(sess.id)}
                        title={isCompleted ? "Mark Planned" : "Mark Completed"}
                      >
                        <Check size={18} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Upcoming Exams & Goals */}
        <div className="dashboard-right">
          {/* Upcoming Exams Card */}
          <div className="card-box">
            <div className="section-header">
              <h3>🎯 Target Exams</h3>
            </div>

            {upcoming_exams.length === 0 ? (
              <p className="empty-text">No upcoming exams defined yet.</p>
            ) : (
              <div className="exams-list">
                {upcoming_exams.map((ex) => (
                  <div key={ex.id} className="exam-item" onClick={() => onViewSchedule(ex.id)}>
                    <div>
                      <h4 className="exam-name">{ex.title}</h4>
                      <span className="exam-date">📅 {ex.exam_date}</span>
                    </div>
                    <div className="exam-countdown">
                      <span className="days-chip">
                        {ex.days_left <= 0 ? "Today!" : `${ex.days_left} days left`}
                      </span>
                      <ArrowRight size={16} color="#64748B" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Goals & Habits Card */}
          <div className="card-box" style={{ marginTop: "1.5rem" }}>
            <div className="section-header">
              <h3>🏆 Study Goals</h3>
              <button
                className="icon-link-btn"
                onClick={() => setShowGoalInput(!showGoalInput)}
              >
                <Plus size={16} />
                <span>Add Goal</span>
              </button>
            </div>

            {showGoalInput && (
              <form onSubmit={handleAddGoal} className="add-goal-form">
                <input
                  type="text"
                  placeholder="e.g. Master Calculus Integration"
                  value={newGoalTitle}
                  onChange={(e) => setNewGoalTitle(e.target.value)}
                  required
                />
                <input
                  type="number"
                  placeholder="Hours"
                  value={newGoalHours}
                  onChange={(e) => setNewGoalHours(e.target.value)}
                  style={{ width: "80px" }}
                />
                <button type="submit" className="primary-btn">Save</button>
              </form>
            )}

            {goals.length === 0 ? (
              <p className="empty-text">Set your first study goal to stay accountable!</p>
            ) : (
              <div className="goals-list">
                {goals.map((g) => (
                  <div key={g.id} className="goal-item">
                    <button
                      className={`goal-checkbox ${g.is_completed ? "checked" : ""}`}
                      onClick={() => handleToggleGoal(g.id)}
                    >
                      {g.is_completed && <Check size={14} color="#ffffff" />}
                    </button>
                    <span className={`goal-title ${g.is_completed ? "done" : ""}`}>
                      {g.title}
                    </span>
                    <span className="goal-target">{g.target_hours} hrs</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
