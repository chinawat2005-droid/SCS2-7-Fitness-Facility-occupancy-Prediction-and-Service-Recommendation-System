"""สมัคร/ล็อกอิน (ฝั่ง B)
  POST /auth/register, POST /auth/login, GET /auth/me
ใช้ PBKDF2 + token ลงลายเซ็น HMAC (ไลบรารีมาตรฐาน) ตั้ง SECRET_KEY ใน environment ก่อนใช้งานจริง
"""
import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import engine

SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32)).encode()
TOKEN_TTL_SECONDS = 7 * 24 * 3600
PBKDF2_ROUNDS = 200_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
MIN_PASSWORD = 6

router = APIRouter(prefix="/auth", tags=["auth"])


def init_users_table():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
        """))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _sign(payload: str) -> str:
    return _b64(hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).digest())


def make_token(user_id: int, now: Optional[float] = None) -> str:
    exp = int((now if now is not None else time.time()) + TOKEN_TTL_SECONDS)
    payload = f"{user_id}.{exp}"
    return f"{payload}.{_sign(payload)}"


def read_token(token: str, now: Optional[float] = None) -> Optional[int]:
    try:
        user_id, exp, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(f"{user_id}.{exp}")):
            return None
        if int(exp) < (now if now is not None else time.time()):
            return None
        return int(user_id)
    except (ValueError, AttributeError):
        return None


def create_user(username: str, password: str, role: str = "user") -> dict:
    """สร้างผู้ใช้ ยก ValueError ถ้า username ซ้ำ (owner/admin สร้างด้วย role='owner' ตรงๆ)"""
    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("INSERT INTO users (username, password_hash, role) VALUES (:u, :p, :r)"),
                {"u": username, "p": hash_password(password), "r": role},
            )
            user_id = res.lastrowid
    except IntegrityError:
        raise ValueError("username ซ้ำ")
    return {"user_id": user_id, "username": username, "role": role}


def _public(row) -> dict:
    return {"user_id": row["user_id"], "username": row["username"], "role": row["role"]}


def current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """Dependency อ่านผู้ใช้จาก Authorization: Bearer <token>"""
    scheme, _, token = (authorization or "").partition(" ")
    user_id = read_token(token.strip()) if scheme.lower() == "bearer" else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบใหม่")
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT user_id, username, role FROM users WHERE user_id = :i"), {"i": user_id}
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบใหม่")
    return _public(row)


class Credentials(BaseModel):
    username: str
    password: str


def _auth_response(user: dict) -> dict:
    return {"access_token": make_token(user["user_id"]), "token_type": "bearer", "user": user}


@router.post("/register", status_code=201)
def register(body: Credentials):
    username = body.username.strip()
    if not USERNAME_RE.match(username):
        raise HTTPException(422, "ชื่อผู้ใช้ต้องยาว 3-30 ตัว ใช้ได้เฉพาะ A-Z a-z 0-9 _ . -")
    if len(body.password) < MIN_PASSWORD:
        raise HTTPException(422, f"รหัสผ่านต้องยาวอย่างน้อย {MIN_PASSWORD} ตัวอักษร")
    try:
        user = create_user(username, body.password)
    except ValueError:
        raise HTTPException(409, "ชื่อผู้ใช้นี้ถูกใช้แล้ว")
    return _auth_response(user)


@router.post("/login")
def login(body: Credentials):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT user_id, username, role, password_hash FROM users WHERE username = :u"),
            {"u": body.username.strip()},
        ).mappings().first()
    stored = row["password_hash"] if row else hash_password("dummy")
    ok = verify_password(body.password, stored)
    if row is None or not ok:
        raise HTTPException(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return _auth_response(_public(row))


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user
