import React from "react";
import { BookOpen, PlusCircle, LogOut, User, Sparkles, Calendar, LayoutDashboard, Bell } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Navbar({ onOpenNewPlan, activeTab, setActiveTab, onOpenAuth }) {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-container">
        {/* Brand */}
        <div className="brand" onClick={() => setActiveTab("dashboard")}>
          <div className="brand-icon">
            <BookOpen size={24} color="#ffffff" />
          </div>
          <div>
            <span className="brand-title">Study Planner AI</span>
            <span className="brand-badge">Gemini Flash</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        {isAuthenticated && (
          <div className="nav-links">
            <button
              className={`nav-btn ${activeTab === "dashboard" ? "active" : ""}`}
              onClick={() => setActiveTab("dashboard")}
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </button>
            <button
              className={`nav-btn ${activeTab === "schedules" ? "active" : ""}`}
              onClick={() => setActiveTab("schedules")}
            >
              <Calendar size={18} />
              <span>My Schedules</span>
            </button>
          </div>
        )}

        {/* Right Actions */}
        <div className="nav-actions">
          {isAuthenticated ? (
            <>
              <div className="alarm-nav-status" title="Study Time Alarm & Desktop Reminders Active">
                <Bell size={13} color="#15803D" />
                <span>Alarm Ready</span>
              </div>

              <button className="primary-btn" onClick={onOpenNewPlan}>
                <Sparkles size={16} />
                <span>AI Study Plan</span>
              </button>


              <div className="user-profile">
                <div className="avatar">
                  <User size={16} />
                </div>
                <span className="user-name">{user?.name}</span>
                <button className="logout-btn" onClick={logout} title="Sign Out">
                  <LogOut size={16} />
                </button>
              </div>
            </>
          ) : (
            <button className="primary-btn" onClick={() => onOpenAuth(true)}>
              <User size={16} />
              <span>Sign In / Sign Up</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
