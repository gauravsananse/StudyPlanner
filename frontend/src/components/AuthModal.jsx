import React, { useState } from "react";
import { X, Lock, Mail, User, ArrowRight, Zap } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function AuthModal({ isOpen, onClose }) {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        if (!name.trim()) throw new Error("Name is required");
        await register(name, email, password);
      }
      onClose();
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setError("");
    setLoading(true);
    try {
      // Try demo login
      await login("student@example.com", "study1234");
      onClose();
    } catch (err) {
      // If demo user doesn't exist yet, auto-register it
      try {
        await register("Alex Rivera", "student@example.com", "study1234");
        onClose();
      } catch (regErr) {
        setError(regErr.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <button className="modal-close" onClick={onClose}>
          <X size={20} />
        </button>

        <div className="modal-header">
          <h2>{isLogin ? "Welcome Back 👋" : "Create Your Student Account 🚀"}</h2>
          <p className="subtitle">
            {isLogin
              ? "Sign in to access your AI study schedules and exam countdowns."
              : "Start organizing your study sessions with personalized AI planning."}
          </p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          {!isLogin && (
            <div className="input-group">
              <label>Full Name</label>
              <div className="input-wrapper">
                <User size={18} className="input-icon" />
                <input
                  type="text"
                  placeholder="e.g. Alex Rivera"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            </div>
          )}

          <div className="input-group">
            <label>Email Address</label>
            <div className="input-wrapper">
              <Mail size={18} className="input-icon" />
              <input
                type="email"
                placeholder="student@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="input-group">
            <label>Password</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button type="submit" className="primary-btn submit-btn" disabled={loading}>
            <span>{loading ? "Processing..." : isLogin ? "Sign In" : "Create Account"}</span>
            <ArrowRight size={16} />
          </button>
        </form>

        <div className="divider">
          <span>OR</span>
        </div>

        <button type="button" className="demo-btn" onClick={handleDemoLogin} disabled={loading}>
          <Zap size={16} color="#EAB308" />
          <span>One-Click Demo Student Sign In</span>
        </button>

        <div className="auth-toggle">
          {isLogin ? "Don't have an account yet?" : "Already have an account?"}{" "}
          <button
            type="button"
            className="toggle-link"
            onClick={() => {
              setIsLogin(!isLogin);
              setError("");
            }}
          >
            {isLogin ? "Sign Up" : "Log In"}
          </button>
        </div>
      </div>
    </div>
  );
}
