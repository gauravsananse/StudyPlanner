# 🎓 Study Planner AI (Full-Stack Web App)

A modern full-stack web application designed to help students organize their exam preparation using **React**, **Vite**, **FastAPI**, and **Google Gemini AI**.

---

## 🌟 Core Features

- **AI-Powered Study Planning**: Students enter their exam date, subjects, topics, and daily study limits. The app calls Google Gemini to generate balanced, personalized study roadmaps.
- **Dynamic Time-Slots**: Breaks down each subject into concrete daily time windows (e.g., `09:00 - 11:00 AM`, `02:00 - 03:30 PM`, `06:30 - 08:00 PM`) with actionable, practical study tasks.
- **Central User Dashboard**:
  - Real-time study hours, sessions completed, and readiness metrics.
  - Today's actionable dynamic study slots with one-click completion toggles.
  - Target exams countdown chips.
  - Personal study goals and streak management.
- **User Authentication**: Secure JWT-based authentication system with registration, login, and password hashing.
- **Schedule Management**: Full schedule timetable with filtering by planned/completed status, subject breakdown, and deletion.

---

## 🛠️ Technical Stack

- **Frontend**: React 18, Vite, Lucide Icons, Modern responsive CSS.
- **Backend**: FastAPI, Uvicorn, SQLite database with foreign keys, PyJWT auth.
- **Intelligence**: Google Gemini Flash API (`google-genai` SDK) for generating intelligent, time-based study content.

---

## 🚀 How to Run on Local Machine (Windows PowerShell)

### Step 1: Open PowerShell in Project Folder

```powershell
cd "c:\Users\gaura\Downloads\AI Based Study Planner"
```

### Step 2: Activate the Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Run the FastAPI Application Server

The FastAPI backend serves both the REST API and the React production build in a single unified process:

```powershell
python backend/run.py
```

Open your browser to:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 💻 Optional: Running in Hot-Reload Development Mode

If you are developing or modifying the React components with instant hot module replacement:

1. **Terminal 1 (Backend)**:
   ```powershell
   python backend/run.py
   ```
2. **Terminal 2 (Frontend)**:
   ```powershell
   cd frontend
   npm run dev
   ```
   Open **[http://localhost:5173](http://localhost:5173)**.

---

## ⚡ Quick Testing / Demo Login

For rapid testing without registration:
1. Click **Sign In / Sign Up** in the navigation bar.
2. Click **⚡ One-Click Demo Student Sign In**.
3. Click **AI Study Plan** to create an AI-generated schedule with dynamic time slots!
