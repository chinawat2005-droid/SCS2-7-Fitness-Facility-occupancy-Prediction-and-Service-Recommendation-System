from math import asin, cos, radians, sin, sqrt
from typing import Optional

from fastapi import FastAPI
from sqlalchemy import inspect, text

from app.database import engine

app = FastAPI(title="Gym Occupancy API")


def haversine_km(lat1, lng1, lat2, lng2):
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


@app.get("/gyms")
def list_gyms(lat: Optional[float] = None, lng: Optional[float] = None):
    with engine.connect() as conn:
        gyms = conn.execute(text("SELECT * FROM gyms ORDER BY gym_id")).mappings().all()

        # ชั่วโมงล่าสุดของแต่ละยิม
        latest = conn.execute(text("""
            SELECT o.gym_id, o.count, o.occupancy_pct, o.level
            FROM occupancy o
            WHERE o.datetime = (
                SELECT MAX(datetime) FROM occupancy WHERE gym_id = o.gym_id
            )
        """)).mappings().all()
        latest = {r["gym_id"]: r for r in latest}

        # คะแนนรีวิวเฉลี่ย (ตาราง reviews ยังไม่มี → ได้ None)
        ratings = {}
        if inspect(engine).has_table("reviews"):
            rows = conn.execute(text(
                "SELECT gym_id, AVG(rating) AS avg_rating FROM reviews GROUP BY gym_id"
            )).mappings().all()
            ratings = {r["gym_id"]: round(r["avg_rating"], 1) for r in rows}

    result = []
    for r in gyms:
        g = dict(r)
        g["equipment"] = g["equipment"].split(";")
        g["facilities"] = g["facilities"].split(";")

        cur = latest.get(g["gym_id"])
        g["current_count"] = int(cur["count"]) if cur else None
        g["current_pct"] = round(float(cur["occupancy_pct"]), 1) if cur else None
        g["current_level"] = cur["level"] if cur else None

        if lat is not None and lng is not None:
            g["distance_km"] = round(haversine_km(lat, lng, g["lat"], g["lng"]), 1)

        g["avg_rating"] = ratings.get(g["gym_id"])
        result.append(g)
    return result

from pathlib import Path
from fastapi.staticfiles import StaticFiles

app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True),
    name="frontend",
)
