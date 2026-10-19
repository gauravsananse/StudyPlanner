import React, { useState, useEffect, useRef } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import Dashboard from "./components/Dashboard";
import ScheduleView from "./components/ScheduleView";
import PlanGeneratorModal from "./components/PlanGeneratorModal";
import AuthModal from "./components/AuthModal";
import AlarmModal from "./components/AlarmModal";
import { Sparkles, Calendar, Clock, CheckCircle, ArrowRight } from "lucide-react";
import { fetchDashboardData, toggleSessionStatus, rescheduleMissedSessions } from "./api";
import { checkForActiveAlarm, showSystemNotification, requestNotificationPermission } from "./utils/alarmManager";
import { startContinuousAlarm, stopContinuousAlarm } from "./utils/alarmSound";

function MainContent() {
  const { isAuthenticated, loading } = useAuth();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [selectedPlanId, setSelectedPlanId] = useState(null);
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [activeAlarmSession, setActiveAlarmSession] = useState(null);
  const alarmCheckIntervalRef = useRef(null);

  // Background Study Alarm Checker: Checks every 25 seconds for active study slots
  useEffect(() => {
    if (!isAuthenticated) return;

    // Pre-request notification permission
    requestNotificationPermission();

    const runAlarmCheck = async () => {
      try {
        const data = await fetchDashboardData();
        if (data && data.today_sessions) {
          const alarmSession = checkForActiveAlarm(data.today_sessions);
          if (alarmSession) {
            setActiveAlarmSession(alarmSession);
            startContinuousAlarm();
            showSystemNotification(
              `⏰ Time to Study: ${alarmSession.subject}`,
              `Topic: ${alarmSession.topic} (${alarmSession.time_slot}). Time to sit down!`
            );
          }
        }
      } catch (e) {
        // silently ignore background polling errors
      }
    };

    // Run immediately once, then interval
    runAlarmCheck();
    alarmCheckIntervalRef.current = setInterval(runAlarmCheck, 25000);

    return () => {
      if (alarmCheckIntervalRef.current) {
        clearInterval(alarmCheckIntervalRef.current);
      }
      stopContinuousAlarm();
    };
  }, [isAuthenticated]);

  const handleCompleteAlarmSession = async (sessionId) => {
    try {
      await toggleSessionStatus(sessionId);
      stopContinuousAlarm();
      setActiveAlarmSession(null);
      // Reload or refresh view
      window.location.reload();
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  const handleRescheduleAlarmSession = async (session) => {
    try {
      stopContinuousAlarm();
      setActiveAlarmSession(null);
      if (session.plan_id) {
        const res = await rescheduleMissedSessions(session.plan_id);
        alert(`✅ ${res.message}`);
        window.location.reload();
      }
    } catch (err) {
      alert("Rescheduling failed: " + err.message);
    }
  };

  const handleViewSchedule = (planId) => {
    setSelectedPlanId(planId);
    setActiveTab("schedules");
  };

  const handlePlanCreated = () => {
    setActiveTab("dashboard");
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="center-container">
        <div className="spinner"></div>
      </div>
    );
  }


  return (
    <div className="app-shell">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenNewPlan={() => {
          if (!isAuthenticated) setIsAuthModalOpen(true);
          else setIsPlanModalOpen(true);
        }}
        onOpenAuth={() => setIsAuthModalOpen(true)}
      />

      <main className="main-content">
        {!isAuthenticated ? (
          /* Landing Screen for Unauthenticated Students */
          <div className="hero-section">
            <div className="hero-content">
              <div className="hero-pill">
                <Sparkles size={16} />
                <span>Powered by Google Gemini Flash & FastAPI</span>
              </div>
              <h1 className="hero-title">
                Smart Exam Preparation <br />
                <span className="gradient-text">Structured by AI</span>
              </h1>
              <p className="hero-description">
                Input your subjects, select your target exam dates, and let intelligent AI break down your syllabus into actionable dynamic time slots with automated tracking.
              </p>

              <div className="hero-actions">
                <button
                  className="primary-btn hero-btn"
                  onClick={() => setIsAuthModalOpen(true)}
                >
                  <span>Start Planning Free</span>
                  <ArrowRight size={18} />
                </button>
              </div>

              {/* Feature Highlights Grid */}
              <div className="features-grid">
                <div className="feature-card">
                  <div className="feature-icon blue">
                    <Sparkles size={24} />
                  </div>
                  <h3>AI-Powered Scheduling</h3>
                  <p>Interleaves subjects and balances cognitive load to maximize retention before exam day.</p>
                </div>

                <div className="feature-card">
                  <div className="feature-icon green">
                    <Clock size={24} />
                  </div>
                  <h3>Dynamic Time-Slots</h3>
                  <p>Assigns concrete morning, afternoon, or evening study windows with actionable milestones.</p>
                </div>

                <div className="feature-card">
                  <div className="feature-icon purple">
                    <Calendar size={24} />
                  </div>
                  <h3>Central Dashboard</h3>
                  <p>Track study streaks, upcoming exam countdowns, and completion percentages in real time.</p>
                </div>
              </div>
            </div>
          </div>
        ) : activeTab === "dashboard" ? (
          <Dashboard
            onOpenNewPlan={() => setIsPlanModalOpen(true)}
            onViewSchedule={handleViewSchedule}
          />
        ) : (
          <ScheduleView
            initialPlanId={selectedPlanId}
            onBackToDashboard={() => setActiveTab("dashboard")}
            onOpenNewPlan={() => setIsPlanModalOpen(true)}
          />
        )}
      </main>

      {/* Modals */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      <PlanGeneratorModal
        isOpen={isPlanModalOpen}
        onClose={() => setIsPlanModalOpen(false)}
        onPlanCreated={handlePlanCreated}
      />

      <AlarmModal
        activeSession={activeAlarmSession}
        onClose={() => {
          stopContinuousAlarm();
          setActiveAlarmSession(null);
        }}
        onCompleteSession={handleCompleteAlarmSession}
        onRescheduleSession={handleRescheduleAlarmSession}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainContent />
    </AuthProvider>
  );
}
