"""
ฟังก์ชันพยากรณ์ความหนาแน่นรายชั่วโมงของยิม (ฝั่ง A ส่งให้ฝั่ง B เรียกใช้)

ใช้ในโค้ดอื่น:
    from ml.forecast import forecast_day
    forecast_day(gym_id=2, date="2026-10-20")

ทดสอบ (รันจากโฟลเดอร์รากของโปรเจกต์):
    python ml/forecast.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # เพื่อ import gen_occupancy_data ที่อยู่โฟลเดอร์ราก

import joblib
import pandas as pd

# ใช้ข้อมูลยิม/วันหยุด/ปฏิทินสอบชุดเดียวกับตอนสร้างข้อมูล (แก้ที่เดียวพอ)
from gen_occupancy_data import BON_EXAM, GYMS, HOLIDAYS

MODEL_PATH = ROOT / "models" / "best_model.joblib"
_bundle = None


def _load_model():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def level(ratio):
    # เกณฑ์เดียวกับ gen_occupancy_data.py
    return "low" if ratio < 0.35 else ("medium" if ratio < 0.65 else "high")


def forecast_day(gym_id, date):
    """พยากรณ์รายชั่วโมงของยิม gym_id ในวันที่ date ('YYYY-MM-DD')
    คืน dict รูปแบบเดียวกับ GET /gyms/{id}/forecast ใน API.md"""
    gym = next((g for g in GYMS if g["gym_id"] == gym_id), None)
    if gym is None:
        raise ValueError(f"ไม่พบ gym_id={gym_id}")

    d = pd.Timestamp(date)
    is_weekend = d.dayofweek >= 5
    open_h, close_h = gym["open_we"] if is_weekend else gym["open_wd"]
    hours = list(range(open_h, close_h))

    # สร้างฟีเจอร์ 6 ตัวให้เหมือนตอนฝึก
    X = pd.DataFrame({
        "gym_id": gym_id,
        "hour": hours,
        "day_of_week": d.dayofweek,
        "is_weekend": int(is_weekend),
        "is_holiday": int(d.strftime("%Y-%m-%d") in HOLIDAYS),
        "is_exam_period": int(gym_id == 4 and BON_EXAM[0] <= d <= BON_EXAM[1]),
    })
    bundle = _load_model()
    X = pd.get_dummies(X, columns=["gym_id"], dtype=int)
    X = X.reindex(columns=bundle["columns"], fill_value=0)  # เรียงคอลัมน์ให้ตรงตอนฝึก

    pred = bundle["model"].predict(X).clip(0, gym["capacity"])
    result_hours = []
    for h, p in zip(hours, pred):
        ratio = p / gym["capacity"]
        result_hours.append({
            "hour": h,
            "predicted_count": int(round(p)),
            "predicted_pct": round(100 * ratio, 1),
            "level": level(ratio),
        })
    return {
        "gym_id": gym_id,
        "date": d.strftime("%Y-%m-%d"),
        "model": bundle["name"],
        "hours": result_hours,
    }


if __name__ == "__main__":
    # ทดสอบ: วันธรรมดา, วันเสาร์, วันหยุด 23 ต.ค.
    for gid, dt in [(2, "2026-10-20"), (2, "2026-10-24"), (4, "2026-10-23")]:
        r = forecast_day(gid, dt)
        print(f"\n=== gym {gid} ({dt}) model={r['model']} ===")
        for row in r["hours"]:
            print(f"{row['hour']:02d}:00  {row['predicted_count']:3d} คน  "
                  f"{row['predicted_pct']:5.1f}%  {row['level']}")