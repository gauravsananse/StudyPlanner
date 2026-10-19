import React, { useState } from "react";
import { X, Sparkles, Plus, Trash2, Calendar, Clock, BookOpen, CheckCircle, ArrowRight } from "lucide-react";
import { generateAIPlan, savePlan } from "../api";

export default function PlanGeneratorModal({ isOpen, onClose, onPlanCreated }) {
  const [title, setTitle] = useState("Midterm Preparation");
  const [examDate, setExamDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 21);
    return d.toISOString().split("T")[0];
  });
  const [dailyHours, setDailyHours] = useState(2.0);
  const [subjects, setSubjects] = useState([
    { name: "Mathematics", topics: "Calculus Derivatives, Integration, Linear Algebra" },
    { name: "Physics", topics: "Mechanics, Newton Laws, Thermodynamics" },
  ]);
  const [preferredSlots, setPreferredSlots] = useState([
    "Morning (09:00 - 10:30 AM)",
    "Evening (06:30 - 08:00 PM)",
  ]);
  const [studyDays, setStudyDays] = useState([
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
  ]);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generatedResult, setGeneratedResult] = useState(null);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const ALL_WEEKDAYS = [
    { full: "Monday", short: "Mon" },
    { full: "Tuesday", short: "Tue" },
    { full: "Wednesday", short: "Wed" },
    { full: "Thursday", short: "Thu" },
    { full: "Friday", short: "Fri" },
    { full: "Saturday", short: "Sat" },
    { full: "Sunday", short: "Sun" },
  ];

  const toggleStudyDay = (dayFull) => {
    if (studyDays.includes(dayFull)) {
      setStudyDays(studyDays.filter((d) => d !== dayFull));
    } else {
      setStudyDays([...studyDays, dayFull]);
    }
  };

  const handleAddSubject = () => {
    setSubjects([...subjects, { name: "", topics: "" }]);
  };

  const handleRemoveSubject = (index) => {
    setSubjects(subjects.filter((_, i) => i !== index));
  };

  const handleSubjectChange = (index, field, value) => {
    const updated = [...subjects];
    updated[index][field] = value;
    setSubjects(updated);
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setGeneratedResult(null);

    try {
      const formattedSubjects = subjects
        .filter((s) => s.name.trim())
        .map((s) => ({
          name: s.name.trim(),
          topics: s.topics
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        }));

      if (formattedSubjects.length === 0) {
        throw new Error("Please provide at least one subject with topics.");
      }

      if (studyDays.length === 0) {
        throw new Error("Please select at least one day in the week when you are available to study.");
      }

      const res = await generateAIPlan({
        title,
        exam_date: examDate,
        subjects: formattedSubjects,
        daily_hours: parseFloat(dailyHours) || 2.0,
        preferred_slots: preferredSlots,
        study_days: studyDays,
      });

      setGeneratedResult(res);
    } catch (err) {
      setError(err.message || "Failed to generate AI plan");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToSchedule = async () => {
    if (!generatedResult) return;
    setSaving(true);
    setError("");

    try {
      const formattedSubjects = subjects
        .filter((s) => s.name.trim())
        .map((s) => ({
          name: s.name.trim(),
          topics: s.topics
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        }));

      await savePlan({
        title,
        exam_date: examDate,
        daily_hours: parseFloat(dailyHours) || 2.0,
        preferred_slots: preferredSlots,
        study_days: studyDays,
        subjects: formattedSubjects,
        sessions: generatedResult.sessions,
      });

      onPlanCreated();
      onClose();
    } catch (err) {
      setError(err.message || "Failed to save plan");
    } finally {
      setSaving(false);
    }
  };



  return (
    <div className="modal-backdrop">
      <div className="modal-card modal-large">
        <button className="modal-close" onClick={onClose}>
          <X size={20} />
        </button>

        <div className="modal-header">
          <div className="modal-badge">
            <Sparkles size={14} />
            <span>Powered by Google Gemini</span>
          </div>
          <h2>AI Study Planner 🧠</h2>
          <p className="subtitle">
            Define your subjects, exam date, and daily study windows. Gemini will dynamically generate a personalized schedule.
          </p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {!generatedResult ? (
          /* Step 1: Input Form */
          <form onSubmit={handleGenerate} className="plan-form">
            <div className="form-row">
              <div className="input-group">
                <label>Exam / Milestone Name</label>
                <div className="input-wrapper">
                  <BookOpen size={18} className="input-icon" />
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Finals / USMLE / SAT"
                    required
                  />
                </div>
              </div>

              <div className="input-group">
                <label>Target Exam Date</label>
                <div className="input-wrapper">
                  <Calendar size={18} className="input-icon" />
                  <input
                    type="date"
                    value={examDate}
                    onChange={(e) => setExamDate(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="input-group">
                <label>Daily Study Target (Hours)</label>
                <div className="input-wrapper">
                  <Clock size={18} className="input-icon" />
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="10"
                    value={dailyHours}
                    onChange={(e) => setDailyHours(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            {/* Dynamic Subjects List */}
            <div className="subjects-section">
              <div className="section-title-row">
                <label>Subjects & Topics</label>
                <button type="button" className="add-sub-btn" onClick={handleAddSubject}>
                  <Plus size={14} />
                  <span>Add Subject</span>
                </button>
              </div>

              {subjects.map((s, idx) => (
                <div key={idx} className="subject-item-row">
                  <input
                    type="text"
                    placeholder="Subject Name (e.g. Biology)"
                    value={s.name}
                    onChange={(e) => handleSubjectChange(idx, "name", e.target.value)}
                    className="subj-name-input"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Topics separated by commas (e.g. Genetics, Cell Structure)"
                    value={s.topics}
                    onChange={(e) => handleSubjectChange(idx, "topics", e.target.value)}
                    className="subj-topics-input"
                    required
                  />
                  {subjects.length > 1 && (
                    <button
                      type="button"
                      className="delete-sub-btn"
                      onClick={() => handleRemoveSubject(idx)}
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Days in a Week Availability */}
            <div className="study-days-section">
              <div className="section-title-row">
                <div>
                  <label>📅 Days in a Week You Can Study</label>
                  <p className="section-desc">
                    Select which days in a week you are available to sit down and study. Click any day to toggle it between <strong>Available</strong> and <strong>Not Available / Off</strong>.
                  </p>
                </div>
                <span className="days-count-badge">
                  {studyDays.length} of 7 days available
                </span>
              </div>

              <div className="days-grid">
                {ALL_WEEKDAYS.map(({ full, short }) => {
                  const isAvailable = studyDays.includes(full);
                  return (
                    <button
                      key={full}
                      type="button"
                      className={`day-box ${isAvailable ? "available" : "off"}`}
                      onClick={() => toggleStudyDay(full)}
                      title={`Click to mark ${full} as ${isAvailable ? "Not Available / Off" : "Available"}`}
                    >
                      <span className="day-name-short">{short}</span>
                      <span className="day-name-full">{full}</span>
                      <span className={`day-status-pill ${isAvailable ? "status-on" : "status-off"}`}>
                        {isAvailable ? "✅ Available" : "🚫 Not Available"}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>



            <button type="submit" className="primary-btn submit-btn" disabled={loading}>
              <Sparkles size={18} />
              <span>{loading ? "Gemini is Crafting Your Schedule..." : "Generate AI Study Plan"}</span>
            </button>
          </form>
        ) : (
          /* Step 2: AI Generated Preview */
          <div className="preview-container">
            <div className="ai-summary-card">
              <div className="ai-summary-header">
                <h4>✨ {generatedResult.overview}</h4>
                <span className="source-tag">{generatedResult.source}</span>
              </div>
              <p className="summary-meta">
                Generated <strong>{generatedResult.sessions.length} actionable sessions</strong> with designated dynamic time slots.
              </p>
            </div>

            <div className="preview-sessions-scroll">
              {generatedResult.sessions.map((sess, i) => (
                <div key={i} className="preview-session-item">
                  <div className="sess-date-slot">
                    <span className="sess-date">📅 {sess.date}</span>
                    <span className="sess-slot">⏱️ {sess.time_slot}</span>
                  </div>
                  <div className="sess-info">
                    <strong>{sess.subject}</strong>: {sess.topic}
                    {sess.actionable_task && (
                      <p className="sess-action">🎯 {sess.actionable_task}</p>
                    )}
                  </div>
                  <span className="sess-duration">{sess.duration_minutes}m</span>
                </div>
              ))}
            </div>

            <div className="preview-actions">
              <button
                type="button"
                className="secondary-btn"
                onClick={() => setGeneratedResult(null)}
              >
                Back / Adjust Settings
              </button>
              <button
                type="button"
                className="primary-btn"
                onClick={handleSaveToSchedule}
                disabled={saving}
              >
                <CheckCircle size={18} />
                <span>{saving ? "Saving Plan..." : "Save to My Schedule"}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
