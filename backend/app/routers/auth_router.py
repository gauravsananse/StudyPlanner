from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db_connection
from ..schemas import TokenOut, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenOut)
def register(user_in: UserRegister):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?;", (user_in.email.lower().strip(),))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        hashed = hash_password(user_in.password)
        cursor.execute(
            """
            INSERT INTO users (name, email, hashed_password, created_at)
            VALUES (?, ?, ?, ?);
            """,
            (user_in.name.strip(), user_in.email.lower().strip(), hashed, now_iso),
        )
        user_id = cursor.lastrowid
        conn.commit()

        user_out = UserOut(
            id=user_id,
            name=user_in.name.strip(),
            email=user_in.email.lower().strip(),
            created_at=now_iso,
        )
        token = create_access_token(data={"sub": str(user_id)})
        return TokenOut(access_token=token, user=user_out)


@router.post("/login", response_model=TokenOut)
def login(user_in: UserLogin):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, hashed_password, created_at FROM users WHERE email = ?;",
            (user_in.email.lower().strip(),),
        )
        row = cursor.fetchone()
        if not row or not verify_password(user_in.password, row["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        user_out = UserOut(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            created_at=row["created_at"],
        )
        token = create_access_token(data={"sub": str(row["id"])})
        return TokenOut(access_token=token, user=user_out)


@router.get("/me", response_model=UserOut)
def get_me(current_user: dict = Depends(get_current_user)):
    return UserOut(**current_user)
