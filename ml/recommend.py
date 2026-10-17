"""
แนะนำยิมที่เหมาะกับผู้ใช้ (ฝั่ง A) ตามสัญญา POST /recommend ใน API.md

คะแนนรวม (0-1) = ผลรวมถ่วงน้ำหนักของ 4 ปัจจัย
    ความหนาแน่น (พยากรณ์ ณ ชั่วโมงที่เลือก)  ยิ่งโล่งยิ่งดี      น้ำหนัก 0.35 (0.50 ถ้า prefer_quiet)
    ระยะทาง                                   ยิ่งใกล้ยิ่งดี       น้ำหนัก 0.30
    อุปกรณ์ที่ต้องการ                         สัดส่วนที่มีครบ     น้ำหนัก 0.20 (ใช้เมื่อผู้ใช้ระบุ)
    คะแนนรีวิวเฉลี่ย                          ยิ่งสูงยิ่งดี        น้ำหนัก 0.15 (ใช้เมื่อมีข้อมูลรีวิว)
ปัจจัยที่ไม่มีข้อมูลจะถูกตัดออก แล้วปรับน้ำหนักที่เหลือให้รวมเป็น 1
ยิมที่ปิดอยู่ในชั่วโมงที่เลือกจะได้คะแนน 0 และอยู่ท้ายสุด

ทดสอบ (รันจากโฟลเดอร์รากของโปรเจกต์):
    python ml/recommend.py
"""
import datetime as dt
import sys
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ml.forecast import GYMS, forecast_day

BKK = dt.timezone(dt.timedelta(hours=7))
W_CROWD, W_DIST, W_EQUIP, W_RATING = 0.35, 0.30, 0.20, 0.15
W_CROWD_QUIET = 0.50
WINDOW = 4  # หาชั่วโมงที่ดีที่สุดในช่วง ± 4 ชั่วโมงจากเวลาที่เลือก
LEVEL_TH = {"low": "โล่ง", "medium": "ปานกลาง", "high": "แน่น"}


def haversine_km(lat1, lng1, lat2, lng2):
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def recommend(lat, lng, date=None, hour=None, need_equipment=None, prefer_quiet=False,
              ratings=None, top_n=5):
    """คืน {'results': [...]} เรียงจากเหมาะสุดไปน้อยสุด
    ratings = {gym_id: คะแนนรีวิวเฉลี่ย 1-5} (ไม่ใส่ = ไม่นำปัจจัยรีวิวมาคิด)"""
    now = dt.datetime.now(BKK)
    date = date or now.date().isoformat()
    hour = now.hour if hour is None else hour
    need = list(need_equipment or [])
    ratings = ratings or {}

    results = []
    for g in GYMS:
        gid = g["gym_id"]
        day = forecast_day(gid, date)
        by_hour = {h["hour"]: h for h in day["hours"]}
        km = haversine_km(lat, lng, g["lat"], g["lng"])
        reasons = [f"ใกล้คุณ {km:.1f} กม."]
        row = by_hour.get(hour)

        if row is None:  # ปิดอยู่
            results.append({"gym_id": gid, "name": g["name"], "score": 0.0,
                            "distance_km": round(km, 1), "predicted_level": "closed",
                            "best_hours": [], "reasons": [f"ปิดอยู่ช่วง {hour:02d}:00"]})
            continue

        # คะแนนแต่ละปัจจัย (0-1) และน้ำหนัก
        crowd = max(0.0, 1 - row["predicted_pct"] / 100)
        if prefer_quiet:
            crowd = crowd ** 2
        parts = [(W_CROWD_QUIET if prefer_quiet else W_CROWD, crowd),
                 (W_DIST, 1 / (1 + km / 5))]
        reasons.append(f"ช่วง {hour:02d}:00 คาดว่า{LEVEL_TH[row['level']]} (~{row['predicted_count']} คน)")

        if need:
            have = set(g["equipment"]) if isinstance(g.get("equipment"), (list, set)) else \
                set(str(g.get("equipment", "")).split(";"))
            missing = [e for e in need if e not in have]
            parts.append((W_EQUIP, (len(need) - len(missing)) / len(need)))
            reasons.append("มีอุปกรณ์ครบตามที่ต้องการ" if not missing
                           else "ไม่มี " + ", ".join(missing))

        if gid in ratings:
            parts.append((W_RATING, (ratings[gid] - 1) / 4))
            reasons.append(f"คะแนนรีวิว {ratings[gid]}")

        total_w = sum(w for w, _ in parts)
        score = sum(w * s for w, s in parts) / total_w

        # ชั่วโมงที่โล่งที่สุดใกล้เวลาที่เลือก
        cands = [h for h in day["hours"] if abs(h["hour"] - hour) <= WINDOW]
        best = sorted(sorted(cands, key=lambda h: h["predicted_pct"])[:2], key=lambda h: h["hour"])

        results.append({"gym_id": gid, "name": g["name"], "score": round(score, 3),
                        "distance_km": round(km, 1), "predicted_level": row["level"],
                        "best_hours": [h["hour"] for h in best], "reasons": reasons})

    results.sort(key=lambda r: r["score"], reverse=True)
    return {"results": results[:top_n]}


if __name__ == "__main__":
    # ผู้ใช้ยืนอยู่แถวมหาวิทยาลัยขอนแก่น
    LAT, LNG = 16.4741, 102.8200
    cases = [
        ("1) ทั่วไป 18:00", dict(date="2026-10-20", hour=18)),
        ("2) ต้องการ squat_rack 18:00", dict(date="2026-10-20", hour=18, need_equipment=["squat_rack"])),
        ("3) ชอบที่เงียบ 18:00", dict(date="2026-10-20", hour=18, prefer_quiet=True)),
        ("4) 22:00 (บางยิมปิด)", dict(date="2026-10-20", hour=22)),
    ]
    for title, kw in cases:
        print("\n==", title)
        for r in recommend(LAT, LNG, **kw)["results"]:
            print(f"  {r['score']:.3f}  {r['name']:<20} {r['distance_km']:>4} กม. "
                  f"{r['predicted_level']:<7} best={r['best_hours']}  | {'; '.join(r['reasons'])}")