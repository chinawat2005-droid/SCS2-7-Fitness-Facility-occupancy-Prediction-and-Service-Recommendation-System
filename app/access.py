"""สิทธิ์เข้า Dashboard ตามบทบาท
  user  = ลูกค้าทั่วไป (เข้า Dashboard ไม่ได้)
  owner = ผู้ดูแลยิม 1 แห่ง (users.gym_id) เห็นเฉพาะข้อมูลของยิมตัวเอง
  admin = ทีมพัฒนา เห็นทุกยิม
"""
from fastapi import Depends, HTTPException
from sqlalchemy import text

from app.auth import current_user, init_users_table
from app.database import engine


def ensure_gym_column():
    """เพิ่มคอลัมน์ users.gym_id ถ้ายังไม่มี (ใช้ซ้ำได้ ไม่ลบข้อมูลเดิม)"""
    init_users_table()
    with engine.begin() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(users)")).fetchall()]
        if "gym_id" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN gym_id INTEGER"))


ensure_gym_column()


def dashboard_user(user: dict = Depends(current_user)) -> dict:
    """ต้องล็อกอินและเป็น owner หรือ admin เท่านั้น (คืน dict ที่มี role, gym_id)"""
    if user["role"] not in ("owner", "admin"):
        raise HTTPException(403, "บัญชีนี้ไม่มีสิทธิ์เข้า Dashboard")
    with engine.connect() as conn:
        gym_id = conn.execute(
            text("SELECT gym_id FROM users WHERE user_id = :i"), {"i": user["user_id"]}
        ).scalar()
    if user["role"] == "owner" and not gym_id:
        raise HTTPException(403, "บัญชีผู้ดูแลยังไม่ได้ผูกกับยิม")
    return {**user, "gym_id": gym_id}


def scope_gym(user: dict, requested) -> int:
    """owner ถูกบังคับเป็นยิมของตัวเองเสมอ (ต่อให้แก้ URL) ส่วน admin ใช้ค่าที่ขอ (0 = ทุกยิม)"""
    if user["role"] == "owner":
        return int(user["gym_id"])
    return int(requested or 0)