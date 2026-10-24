"""สร้าง/อัปเดตบัญชีผู้ดูแลยิมและทีมพัฒนา (รันบนเครื่องที่จะใช้เดโม)
    python -m app.create_accounts
รหัสผ่านถามตอนรัน ไม่เก็บในโค้ด เพราะรีโปเป็นสาธารณะ รันซ้ำได้ (มีบัญชีอยู่แล้วจะอัปเดตให้)
"""
from getpass import getpass

from sqlalchemy import text

from app.access import ensure_gym_column
from app.auth import MIN_PASSWORD, hash_password
from app.database import engine

# (username, role, gym_id)  gym_id ตามไฟล์ data/gyms.csv
ACCOUNTS = [
    ("admin_boys", "owner", 1),      # The Boys Gym Club
    ("admin_mega", "owner", 2),      # Mega Gym
    ("admin_infinity", "owner", 3),  # Infinity Gym
    ("admin_bon", "owner", 4),       # Bon Fitness (KKU)
    ("admin_nppark", "owner", 5),    # NP Park
    ("dev_chinnawat", "admin", None),
    ("dev_chatdanay", "admin", None),
]


def main():
    ensure_gym_column()
    pw = getpass(f"ตั้งรหัสผ่านสำหรับทุกบัญชี (อย่างน้อย {MIN_PASSWORD} ตัว): ")
    if len(pw) < MIN_PASSWORD:
        raise SystemExit("รหัสผ่านสั้นเกินไป")
    with engine.begin() as conn:
        for username, role, gym_id in ACCOUNTS:
            exists = conn.execute(
                text("SELECT user_id FROM users WHERE username = :u"), {"u": username}
            ).scalar()
            if exists:
                conn.execute(
                    text("UPDATE users SET password_hash=:p, role=:r, gym_id=:g WHERE username=:u"),
                    {"p": hash_password(pw), "r": role, "g": gym_id, "u": username},
                )
            else:
                conn.execute(
                    text("INSERT INTO users (username, password_hash, role, gym_id) VALUES (:u,:p,:r,:g)"),
                    {"u": username, "p": hash_password(pw), "r": role, "g": gym_id},
                )
            print(f"{username:<16} {role:<6} gym_id={gym_id}")
    print("เสร็จแล้ว")


if __name__ == "__main__":
    main()