import React, { useState, useEffect } from "react";
import { 
  Calendar, Clock, CheckCircle, Trash2, Filter, 
  ArrowLeft, Check, Sparkles, BookOpen, RefreshCw, AlertTriangle
} from "lucide-react";
import { 
  fetchPlans, 
  fetchPlanDetails, 
  toggleSessionStatus, 
  deletePlan,
  rescheduleMissedSessions,
  markSessionMissed
} from "../api";

export default function ScheduleView({ initialPlanId, onBackToDashboard, onOpenNewPlan }) {
  const [plans, setPlans] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState(initialPlanId || null);
  const [planDetails, setPlanDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("all");
  const [rescheduling, setRescheduling] = useState(false);

  const loadPlans = async () => {
    try {
      const allPlans = await fetchPlans();
      setPlans(allPlans);
      if (allPlans.length > 0 && !selectedPlanId) {
        setSelectedPlanId(allPlans[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadDetails = async (id) => {
    if (!id) return;
    try {
      const details = await fetchPlanDetails(id);
      setPlanDetails(details);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadPlans();
  }, []);

  useEffect(() => {
    if (selectedPlanId) {
      loadDetails(selectedPlanId);
    }
  }, [selectedPlanId]);

  const handleToggle = async (sessionId) => {
    try {
      await toggleSessionStatus(sessionId);
      loadDetails(selectedPlanId);
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  const handleMarkMissed = async (sessionId) => {
    try {
      await markSessionMissed(sessionId);
      await loadDetails(selectedPlanId);
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  const handleReschedule = async () => {
    if (!selectedPlanId) return;
    setRescheduling(true);
    try {
      const res = await rescheduleMissedSessions(selectedPlanId);
      alert("✅ " + res.message);
      await loadDetails(selectedPlanId);
    } catch (err) {
      alert("Rescheduling failed: " + err.message);
    } finally {
      setRescheduling(false);
    }
  };

  const handleDeletePlan = async (id) => {
    if (!confirm("Are you sure you want to delete this study schedule?")) return;
    try {
      await deletePlan(id);
      const remaining = plans.filter((p) => p.id !== id);
      setPlans(remaining);
      setSelectedPlanId(remaining.length > 0 ? remaining[0].id : null);
      setPlanDetails(null);
    } catch (err) {
      alert(err.message);
    }
  };


  if (loading) {
    return <div className="center-container"><div className="spinner"></div></div>;
  }

  if (plans.length === 0) {
    return (
      <div className="empty-container">
        <BookOpen size={48} color="#94A3B8" />
        <h2>No study plans created yet</h2>
        <p>Use the AI Study Planner to craft your first dynamic schedule.</p>
        <button className="primary-btn" onClick={onOpenNewPlan}>
          <Sparkles size={18} />
          <span>Generate Plan</span>
        </button>
      </div>
    );
  }

  const sessions = planDetails?.sessions || [];
  const filteredSessions = sessions.filter((s) => {
    if (filterStatus === "planned") return s.status === "Planned";
    if (filterStatus === "completed") return s.status === "Completed";
    if (filterStatus === "missed") return s.status === "Missed";
    return true;
  });

  return (
    <div className="schedule-content">
      {/* Top Header */}
      <div className="schedule-header">
        <button className="back-link" onClick={onBackToDashboard}>
          <ArrowLeft size={16} />
          <span>Back to Dashboard</span>
        </button>

        {/* Plan Selector Dropdown */}
        <div className="plan-select-wrapper">
          <label>Select Plan:</label>
          <select
            value={selectedPlanId || ""}
            onChange={(e) => setSelectedPlanId(Number(e.target.value))}
            className="plan-dropdown"
          >
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} (Exam: {p.exam_date})
              </option>
            ))}
          </select>
        </div>
      </div>

      {planDetails && (
        <>
          {/* Plan Meta Banner */}
          <div className="plan-meta-banner">
            <div>
              <h2>{planDetails.plan.title}</h2>
              <div className="meta-tags">
                <span className="meta-tag">📅 Target: {planDetails.plan.exam_date}</span>
                <span className="meta-tag">⏱️ {planDetails.plan.daily_hours} hrs/day</span>
                <span className="meta-tag">📚 {planDetails.subjects.length} Subjects</span>
                {planDetails.plan.study_days && (
                  <span className="meta-tag study-days-tag">
                    🗓️ {planDetails.plan.study_days.length} Study Days/wk
                  </span>
                )}
              </div>
            </div>

            <div className="plan-banner-actions">
              <button
                className="reschedule-plan-btn"
                onClick={handleReschedule}
                disabled={rescheduling}
                title="Reschedule all missed sessions across remaining days"
              >
                <RefreshCw size={16} className={rescheduling ? "spin" : ""} />
                <span>{rescheduling ? "Rescheduling..." : "⚡ Reschedule Missed"}</span>
              </button>

              <button
                className="delete-plan-btn"
                onClick={() => handleDeletePlan(planDetails.plan.id)}
                title="Delete Plan"
              >
                <Trash2 size={18} />
                <span>Delete Plan</span>
              </button>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="filter-bar">
            <span className="filter-label">Filter Sessions:</span>
            <button
              className={`filter-chip ${filterStatus === "all" ? "active" : ""}`}
              onClick={() => setFilterStatus("all")}
            >
              All ({sessions.length})
            </button>
            <button
              className={`filter-chip ${filterStatus === "planned" ? "active" : ""}`}
              onClick={() => setFilterStatus("planned")}
            >
              Planned ({sessions.filter((s) => s.status === "Planned").length})
            </button>
            <button
              className={`filter-chip ${filterStatus === "completed" ? "active" : ""}`}
              onClick={() => setFilterStatus("completed")}
            >
              Completed ({sessions.filter((s) => s.status === "Completed").length})
            </button>
            <button
              className={`filter-chip ${filterStatus === "missed" ? "active" : ""}`}
              onClick={() => setFilterStatus("missed")}
            >
              Missed ({sessions.filter((s) => s.status === "Missed").length})
            </button>
          </div>

          {/* Sessions List */}
          <div className="full-schedule-list">
            {filteredSessions.length === 0 ? (
              <p className="empty-text">No sessions match the selected filter.</p>
            ) : (
              filteredSessions.map((s) => {
                const isCompleted = s.status === "Completed";
                const isMissed = s.status === "Missed";
                return (
                  <div key={s.id} className={`schedule-item ${isCompleted ? "done" : isMissed ? "missed" : ""}`}>
                    <div className="item-date-slot">
                      <span className="item-date">📅 {s.date}</span>
                      <span className="item-slot">⏱️ {s.time_slot}</span>
                      {isMissed && <span className="status-badge-missed">Missed</span>}
                    </div>

                    <div className="item-details">
                      <div className="item-title-row">
                        <span className="subject-pill">{s.subject}</span>
                        <h4>{s.topic}</h4>
                      </div>
                      {s.actionable_task && (
                        <p className="item-action">🎯 {s.actionable_task}</p>
                      )}
                    </div>

                    <div className="item-right">
                      <span className="item-duration">{s.duration_minutes}m</span>
                      {!isCompleted && !isMissed && (
                        <button
                          className="item-miss-btn"
                          onClick={() => handleMarkMissed(s.id)}
                          title="Flag as missed"
                        >
                          <AlertTriangle size={14} />
                          <span>Missed</span>
                        </button>
                      )}
                      <button
                        className={`item-toggle-btn ${isCompleted ? "checked" : ""}`}
                        onClick={() => handleToggle(s.id)}
                      >
                        <Check size={18} />
                        <span>{isCompleted ? "Completed" : "Mark Done"}</span>
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
}

