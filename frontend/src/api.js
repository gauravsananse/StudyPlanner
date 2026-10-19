const API_BASE_URL = "http://localhost:8000/api";

function getAuthHeaders() {
  const token = localStorage.getItem("study_token");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = "Something went wrong";
    try {
      const errData = await response.json();
      errorMsg = errData.detail || errData.message || errorMsg;
    } catch (e) {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

// Authentication
export async function registerUser(name, email, password) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function loginUser(email, password) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser() {
  return apiRequest("/auth/me");
}

// Dashboard
export async function fetchDashboardData() {
  return apiRequest("/dashboard");
}

export async function createGoal(title, targetHours) {
  return apiRequest("/dashboard/goals", {
    method: "POST",
    body: JSON.stringify({ title, target_hours: targetHours }),
  });
}

export async function toggleGoal(goalId) {
  return apiRequest(`/dashboard/goals/${goalId}/toggle`, {
    method: "PATCH",
  });
}

// Plans
export async function generateAIPlan(payload) {
  return apiRequest("/plans/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function savePlan(payload) {
  return apiRequest("/plans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchPlans() {
  return apiRequest("/plans");
}

export async function fetchPlanDetails(planId) {
  return apiRequest(`/plans/${planId}`);
}

export async function toggleSessionStatus(sessionId) {
  return apiRequest(`/plans/sessions/${sessionId}/toggle`, {
    method: "PATCH",
  });
}

export async function markSessionMissed(sessionId) {
  return apiRequest(`/plans/sessions/${sessionId}/miss`, {
    method: "PATCH",
  });
}

export async function rescheduleMissedSessions(planId) {
  return apiRequest(`/plans/${planId}/reschedule-missed`, {
    method: "POST",
  });
}

export async function deletePlan(planId) {
  return apiRequest(`/plans/${planId}`, {
    method: "DELETE",
  });
}

