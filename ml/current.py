"""
ประมาณจำนวนคนในยิม "ณ เวลานี้" (ฝั่ง A) ใช้โมเดลพยากรณ์ของชั่วโมงปัจจุบัน

ใช้ในโค้ดอื่น:
    from ml.current import forecast_now
    forecast_now(2)                              # เวลาปัจจุบัน (เวลาไทย)
    forecast_now(2, dt.datetime(2026, 10, 28, 18, 30))  # จำลองเวลา เช่นตอนเดโม

ทดสอบ (รันจากโฟลเดอร์รากของโปรเจกต์):
    python ml/current.py
"""
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ml.forecast import GYMS, forecast_day

BKK = dt.timezone(dt.timedelta(hours=7))  # เวลาไทย (ไม่มี DST)


def forecast_now(gym_id, at=None):
    """คืน dict ของจำนวนคนที่คาดว่าอยู่ในยิม ณ เวลา `at` (ไม่ใส่ = ตอนนี้ เวลาไทย)
    ถ้ายิมปิดอยู่: is_open=False, predicted_count=0, level="closed" """
    if at is None:
        at = dt.datetime.now(BKK)
    elif at.tzinfo is not None:
        at = at.astimezone(BKK)

    gym = next((g for g in GYMS if g["gym_id"] == gym_id), None)
    if gym is None:
        raise ValueError(f"ไม่พบ gym_id={gym_id}")

    day = forecast_day(gym_id, at.date().isoformat())
    row = next((h for h in day["hours"] if h["hour"] == at.hour), None)

    result = {
        "gym_id": gym_id,
        "capacity": gym["capacity"],
        "at": at.strftime("%Y-%m-%dT%H:%M"),
        "hour": at.hour,
        "model": day["model"],
    }
    if row is None:  # นอกเวลาเปิดทำการ
        return {**result, "is_open": False, "predicted_count": 0,
                "predicted_pct": 0.0, "level": "closed"}
    return {**result, "is_open": True, "predicted_count": row["predicted_count"],
            "predicted_pct": float(row["predicted_pct"]), "level": row["level"]}


if __name__ == "__main__":
    for gid in (1, 2, 3, 4, 5):
        print(forecast_now(gid))
    print("--- จำลองเวลา 2026-10-28 18:30 ---")
    print(forecast_now(2, dt.datetime(2026, 10, 28, 18, 30)))
    print("--- จำลองเวลา 2026-10-20 03:00 (Mega Gym ปิด) ---")
    print(forecast_now(2, dt.datetime(2026, 10, 20, 3, 0)))