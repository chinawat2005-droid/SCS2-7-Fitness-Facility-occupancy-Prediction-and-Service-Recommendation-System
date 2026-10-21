import json

import pandas as pd
from sqlalchemy import text

from app.database import engine

DDL = """
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    gym_id INTEGER NOT NULL,
    user_id INTEGER,
    rating INTEGER NOT NULL,
    text TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    aspects TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

df = pd.read_csv("data/reviews_gym.csv", encoding="utf-8-sig")
with engine.begin() as conn:
    conn.execute(text(DDL))
    conn.execute(text("DELETE FROM reviews WHERE user_id IS NULL"))  # ลบเฉพาะรีวิวจำลอง
    for r in df.itertuples():
        conn.execute(
            text("INSERT INTO reviews (gym_id, user_id, rating, text, sentiment, aspects, created_at) "
                 "VALUES (:g, NULL, :r, :t, :s, :a, :c)"),
            {"g": int(r.gym_id), "r": int(r.rating), "t": r.text, "s": r.sentiment,
             "a": json.dumps(r.aspects.split(";"), ensure_ascii=False), "c": r.created_at},
        )
    n = conn.execute(text("SELECT COUNT(*) FROM reviews")).scalar()
print(f"นำเข้า {len(df)} รายการ (ในตารางมี {n})")