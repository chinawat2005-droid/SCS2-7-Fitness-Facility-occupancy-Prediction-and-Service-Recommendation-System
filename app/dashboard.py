import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.database import engine

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

STATES = ("รอดำเนินการ", "กำลังแก้", "แก้แล้ว")
ASPECT_TH = {
    "equipment": "อุปกรณ์/เครื่องเล่น",
    "cleanliness": "ความสะอาด",
    "air_conditioning": "เครื่องปรับอากาศ",
    "staff": "พนักงาน",
    "service": "การบริการ",
    "crowding": "ความแออัด",
    "price": "ราคา",
}
ACTION_TH = {
    "equipment": "ตรวจสอบ/ซ่อมบำรุงอุปกรณ์",
    "cleanliness": "เพิ่มรอบทำความสะอาด",
    "air_conditioning": "ตรวจระบบปรับอากาศ",
    "staff": "ทบทวนการดูแลของพนักงาน",
    "service": "ปรับปรุงขั้นตอนบริการ",
    "crowding": "จัดการจำนวนผู้ใช้ในช่วงแออัด",
    "price": "ทบทวนโปรโมชันและราคา",
}
PEAK_THRESHOLD = 50  # เปอร์เซ็นต์ที่ถือว่าหนาแน่น (ค่าเฉลี่ย)

with engine.begin() as _conn:
    _conn.execute(text(
        "CREATE TABLE IF NOT EXISTS operator_issue_status ("
        "gym_id INTEGER NOT NULL, issue_key TEXT NOT NULL, state TEXT NOT NULL, "
        "PRIMARY KEY (gym_id, issue_key))"
    ))


class StatusUpdate(BaseModel):
    gym_id: int = 0  # 0 = ทุกสาขา
    issue_key: str
    state: str


def _hourly(conn, gym_id):
    sql = "SELECT hour, AVG(occupancy_pct) AS pct FROM occupancy"
    params = {}
    if gym_id:
        sql += " WHERE gym_id = :g"
        params["g"] = gym_id
    sql += " GROUP BY hour ORDER BY hour"
    rows = conn.execute(text(sql), params).mappings().all()
    values = [float(r["pct"] or 0) for r in rows]
    scale = 100 if values and max(values) <= 1.5 else 1  # รองรับทั้งสเกล 0-1 และ 0-100
    return [{"hour": int(r["hour"]), "pct": round(float(r["pct"] or 0) * scale, 1)} for r in rows]


def _neg_aspects(conn, gym_id):
    sql = "SELECT aspects FROM reviews WHERE sentiment = 'neg'"
    params = {}
    if gym_id:
        sql += " AND gym_id = :g"
        params["g"] = gym_id
    counts = {}
    for r in conn.execute(text(sql), params).mappings().all():
        try:
            for a in json.loads(r["aspects"] or "[]"):
                counts[a] = counts.get(a, 0) + 1
        except (ValueError, TypeError):
            continue
    return counts


@router.get("/summary")
def summary(gym_id: Optional[int] = None):
    g = gym_id or 0
    with engine.connect() as conn:
        hourly = _hourly(conn, g)
        neg = _neg_aspects(conn, g)
        saved = {
            r["issue_key"]: r["state"]
            for r in conn.execute(
                text("SELECT issue_key, state FROM operator_issue_status WHERE gym_id = :g"),
                {"g": g},
            ).mappings().all()
        }
        total_reviews = conn.execute(
            text("SELECT COUNT(*) FROM reviews" + (" WHERE gym_id = :g" if g else "")),
            {"g": g} if g else {},
        ).scalar()
        gyms = [dict(r) for r in conn.execute(
            text("SELECT gym_id, name FROM gyms ORDER BY gym_id")).mappings().all()]

    problems = []
    peak_hours = [h["hour"] for h in hourly if h["pct"] >= PEAK_THRESHOLD]
    if peak_hours:
        problems.append({
            "key": "peak_hours",
            "title": "ช่วงเวลาหนาแน่น: " + ", ".join(str(h) + ":00" for h in peak_hours),
            "count": len(peak_hours),
            "action": "แนะนำเวลาใช้งานทางเลือกให้ผู้ใช้",
        })
    for aspect, n in sorted(neg.items(), key=lambda kv: -kv[1]):
        problems.append({
            "key": "aspect:" + aspect,
            "title": "รีวิวเชิงลบเรื่อง" + ASPECT_TH.get(aspect, aspect),
            "count": n,
            "action": ACTION_TH.get(aspect, "ตรวจสอบและแก้ไข"),
        })
    for p in problems:
        p["state"] = saved.get(p["key"], STATES[0])

    peak = max(hourly, key=lambda h: h["pct"]) if hourly else None
    avg = round(sum(h["pct"] for h in hourly) / len(hourly), 1) if hourly else 0
    return {
        "gym_id": g,
        "gyms": gyms,
        "states": list(STATES),
        "kpi": {
            "avg_occupancy_pct": avg,
            "peak_hour": peak["hour"] if peak else None,
            "peak_pct": peak["pct"] if peak else None,
            "total_reviews": total_reviews,
            "open_problems": sum(1 for p in problems if p["state"] != "แก้แล้ว"),
        },
        "problems": problems,
        "occupancy_by_hour": hourly,
    }


@router.post("/status")
def update_status(body: StatusUpdate):
    if body.state not in STATES:
        raise HTTPException(400, "สถานะไม่ถูกต้อง")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO operator_issue_status (gym_id, issue_key, state) "
                "VALUES (:g, :k, :s) "
                "ON CONFLICT(gym_id, issue_key) DO UPDATE SET state = :s"
            ),
            {"g": body.gym_id, "k": body.issue_key, "s": body.state},
        )
    return {"ok": True}
