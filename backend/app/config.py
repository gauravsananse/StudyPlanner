import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current folder and parent folders
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "study-planner-ai-secret-jwt-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

DATABASE_PATH = str(Path(__file__).resolve().parent.parent / "study_planner_app.db")
