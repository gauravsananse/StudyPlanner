import React from "react";
import { Bell, Clock, CheckCircle, RefreshCw, X, BookOpen, AlertTriangle } from "lucide-react";
import { stopContinuousAlarm } from "../utils/alarmSound";
import { dismissSessionAlarm, snoozeSessionAlarm } from "../utils/alarmManager";

export default function AlarmModal({
  activeSession,
  onClose,
  onCompleteSession,
  onRescheduleSession,
}) {
  if (!activeSession) return null;

  const handleImStudying = () => {
    stopContinuousAlarm();
    dismissSessionAlarm(activeSession.id);
    onClose();
  };

  const handleComplete = async () => {
    stopContinuousAlarm();
    dismissSessionAlarm(activeSession.id);
    if (onCompleteSession) {
      await onCompleteSession(activeSession.id);
    }
    onClose();
  };

  const handleSnooze = () => {
    stopContinuousAlarm();
    snoozeSessionAlarm(activeSession.id, 5);
    onClose();
  };

  const handleMissedReschedule = async () => {
    stopContinuousAlarm();
    dismissSessionAlarm(activeSession.id);
    if (onRescheduleSession) {
      await onRescheduleSession(activeSession);
    }
    onClose();
  };

  return (
    <div className="modal-backdrop alarm-backdrop">
      <div className="modal-content alarm-modal-card">
        {/* Animated Alarm Icon */}
        <div className="alarm-header-visual">
          <div className="alarm-ring-pulse">
            <Bell size={42} className="alarm-bell-icon" />
          </div>
          <span className="alarm-status-badge">⏰ Study Time Alarm Active</span>
        </div>

        <div className="alarm-title-block">
          <h2>Time to Sit Down and Study!</h2>
          <p className="alarm-subtitle">
            Your planned study session is starting right now. Focused preparation leads to exam mastery!
          </p>
        </div>

        {/* Session Card Info */}
        <div className="alarm-session-detail">
          <div className="alarm-slot-row">
            <span className="slot-subject-badge">{activeSession.subject}</span>
            <span className="slot-time-pill">
              <Clock size={14} />
              {activeSession.time_slot}
            </span>
          </div>

          <h3 className="alarm-topic-name">{activeSession.topic}</h3>

          {activeSession.actionable_task && (
            <div className="alarm-action-box">
              <strong>🎯 Your Action Directive:</strong>
              <p>{activeSession.actionable_task}</p>
            </div>
          )}

          <div className="alarm-meta-line">
            <span>⏱️ Session Duration: <strong>{activeSession.duration_minutes || 90} mins</strong></span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="alarm-action-grid">
          <button className="primary-btn alarm-primary-btn" onClick={handleImStudying}>
            <BookOpen size={18} />
            <span>I'm Sitting Down to Study</span>
          </button>

          <button className="success-btn" onClick={handleComplete}>
            <CheckCircle size={18} />
            <span>Mark Completed</span>
          </button>

          <button className="secondary-btn" onClick={handleSnooze}>
            <Clock size={16} />
            <span>Snooze (5 mins)</span>
          </button>

          <button className="warning-btn" onClick={handleMissedReschedule}>
            <RefreshCw size={16} />
            <span>Missed? Reschedule to Exam</span>
          </button>
        </div>
      </div>
    </div>
  );
}
