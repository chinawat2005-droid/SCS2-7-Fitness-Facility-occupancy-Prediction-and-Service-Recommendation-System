"""
สร้างข้อมูลจำลองความหนาแน่นฟิตเนสรายชั่วโมง (Fitness Occupancy Prediction)
ใช้: python gen_occupancy_data.py
ผลลัพธ์: data/gyms.csv, data/occupancy.csv

หมายเหตุ: ทุกตัวเลข (ความจุ, รูปแบบชั่วโมงพีค, อุปกรณ์, พิกัด) เป็นสมมติฐานเพื่อสาธิตแนวคิด
ไม่ใช่ข้อมูลจริงของยิม ต้องบอกในสไลด์ว่าเป็นข้อมูลจำลอง
ค่าที่ต้องตรวจ/แก้ให้ตรงของจริง ถูกมาร์กด้วย TODO
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

END_DATE = pd.Timestamp("2026-10-14")  # วันสุดท้ายของข้อมูล
N_DAYS = 120                           # ~4 เดือน
TEST_DAYS = 14                         # 14 วันสุดท้ายใช้เป็นชุดทดสอบ (แบ่งตามเวลา)

# TODO: ตรวจวันหยุดนักขัตฤกษ์ให้ตรงปฏิทินอีกครั้ง
HOLIDAYS = {
    "2026-07-28", "2026-07-29", "2026-07-30", "2026-08-12", "2026-10-13", "2026-10-23",
}

# สมมติฐานสำหรับ Bon Fitness (ยิมในมหาวิทยาลัย) -- TODO: ปรับให้ตรงปฏิทินการศึกษาจริง
BON_BREAK_END = pd.Timestamp("2026-08-02")                 # ก่อนหน้านี้ = ปิดเทอม
BON_EXAM = (pd.Timestamp("2026-09-14"), pd.Timestamp("2026-09-25"))  # ช่วงสอบกลางภาค

# กำหนดบุคลิกของแต่ละยิม
# peaks = [(ชั่วโมงกลางพีค, ความกว้าง, น้ำหนัก)]
GYMS = [
    dict(
        gym_id=1, name="The Boys Gym Club", capacity=80, peak_util=0.85,
        open_wd=(7, 22), open_we=(8, 20),
        peaks_wd=[(18.5, 1.6, 1.0), (7.8, 1.0, 0.25)],
        peaks_we=[(10.5, 2.0, 0.7), (16.0, 2.0, 0.5)],
        lat=16.45960203194147, lng=102.82303792883634,  # TODO: ใส่พิกัดจริง
        equipment="free_weights;machine;cable;treadmill;dumbbell_to_50kg",
        facilities="locker;shower;parking;air_conditioning",
    ),
    dict(
        gym_id=2, name="Mega Gym", capacity=120, peak_util=0.90,
        open_wd=(6, 23), open_we=(7, 21),
        peaks_wd=[(18.5, 1.5, 1.0), (7.0, 1.0, 0.45), (12.5, 1.0, 0.2)],
        peaks_we=[(10.0, 2.0, 0.8), (17.0, 2.0, 0.6)],
        lat=16.436750255717545, lng=102.84864576441815,  # TODO: ใส่พิกัดจริง
        equipment="treadmill;elliptical;smith_machine;cable;free_weights;leg_press;rowing",
        facilities="locker;shower;sauna;parking;air_conditioning;towel",
    ),
    dict(
        gym_id=3, name="Infinity Gym", capacity=60, peak_util=0.80,
        open_wd=(6, 23), open_we=(6, 23),   
        peaks_wd=[(19.0, 2.0, 0.8), (23.5, 1.8, 0.55), (6.5, 1.2, 0.3)],
        peaks_we=[(11.0, 2.5, 0.6), (22.0, 2.0, 0.5)],
        lat=16.42125222406619 , lng=102.82001486441816,  # TODO: ใส่พิกัดจริง
        equipment="free_weights;squat_rack;treadmill;cable;functional_area",
        facilities="locker;shower;parking;24h_access",
    ),
    dict(
        gym_id=4, name="Bon Fitness (KKU)", capacity=100, peak_util=0.85,
        open_wd=(8, 21), open_we=(10, 19),
        peaks_wd=[(17.5, 1.4, 1.0), (12.5, 0.8, 0.25)],
        peaks_we=[(16.0, 2.0, 0.45)],
        lat=16.4774073351376, lng=102.81880641045419,  # ประมาณตำแหน่งใน มข. TODO: ใส่พิกัดจริง
        equipment="treadmill;cable;free_weights;machines;stationary_bike",
        facilities="locker;shower;air_conditioning",
    ),
    dict(
        gym_id=5, name="NP Park", capacity=50, peak_util=0.80,
        open_wd=(6, 21), open_we=(6, 20),
        peaks_wd=[(6.5, 1.0, 0.7), (18.0, 1.5, 0.8)],
        peaks_we=[(8.0, 1.8, 1.0), (17.0, 1.5, 0.45)],
        lat=16.483091798128942,  lng=102.81543046441817,  # TODO: ใส่พิกัดจริง
        equipment="free_weights;treadmill;machines;outdoor_area",
        facilities="parking;shower",
    ),
]

# ตัวคูณตามวันในสัปดาห์ (0=จันทร์)
DOW_MULT = {0: 1.08, 1: 1.00, 2: 1.00, 3: 0.95, 4: 0.85, 5: 1.00, 6: 0.90}


def shape(hour, peaks):
    """รวม Gaussian bump หลายลูก แล้ว cap ที่ 1.0"""
    s = sum(w * np.exp(-0.5 * ((hour - mu) / sd) ** 2) for mu, sd, w in peaks)
    return min(s, 1.0)


def level(ratio):
    # เกณฑ์ระดับ: น้อย < 35%, ปานกลาง < 65%, มาก >= 65%
    return "low" if ratio < 0.35 else ("medium" if ratio < 0.65 else "high")


def generate():
    dates = pd.date_range(end=END_DATE, periods=N_DAYS, freq="D")
    rows = []
    for g in GYMS:
        for d in dates:
            is_we = d.dayofweek >= 5
            is_hol = d.strftime("%Y-%m-%d") in HOLIDAYS
            lo, hi = g["open_we"] if is_we else g["open_wd"]
            peaks = g["peaks_we"] if is_we else g["peaks_wd"]

            # ปัจจัยระดับวัน (ใช้ร่วมกันทั้งวัน -> ทำให้พยากรณ์ไม่เป๊ะ)
            day_mult = rng.lognormal(0, 0.10) * DOW_MULT[d.dayofweek]
            if is_hol:
                day_mult *= 0.65
            is_exam = False
            if g["gym_id"] == 4:
                if d < BON_BREAK_END:
                    day_mult *= 0.55
                if BON_EXAM[0] <= d <= BON_EXAM[1]:
                    day_mult *= 0.75
                    is_exam = True
            if rng.random() < 0.02:            # วันผิดปกติ (ฝนตก/ไฟดับ/โปรโมชัน)
                day_mult *= rng.choice([0.5, 1.3])

            for h in range(lo, hi):
                mean = g["capacity"] * g["peak_util"] * shape(h, peaks) * day_mult
                cnt = rng.poisson(max(mean, 0)) + rng.normal(0, 0.04 * g["capacity"])
                cnt = int(np.clip(round(cnt), 0, g["capacity"]))
                ratio = cnt / g["capacity"]
                rows.append(dict(
                    gym_id=g["gym_id"], gym_name=g["name"],
                    datetime=d + pd.Timedelta(hours=h), date=d.date(), hour=h,
                    day_of_week=d.dayofweek, is_weekend=int(is_we),
                    is_holiday=int(is_hol), is_exam_period=int(is_exam),
                    count=cnt, capacity=g["capacity"],
                    occupancy_pct=round(100 * ratio, 1), level=level(ratio),
                ))
    return pd.DataFrame(rows)


def main():
    out = Path("data")
    out.mkdir(exist_ok=True)

    gyms = pd.DataFrame([
        {k: g[k] for k in ("gym_id", "name", "capacity", "lat", "lng", "equipment", "facilities")}
        | {"open_weekday": f"{g['open_wd'][0]:02d}:00-{g['open_wd'][1] % 24:02d}:00",
           "open_weekend": f"{g['open_we'][0]:02d}:00-{g['open_we'][1] % 24:02d}:00"}
        for g in GYMS
    ])
    gyms.to_csv(out / "gyms.csv", index=False, encoding="utf-8-sig")

    df = generate()
    df.to_csv(out / "occupancy.csv", index=False, encoding="utf-8-sig")

    cutoff = df["datetime"].max().normalize() - pd.Timedelta(days=TEST_DAYS - 1)
    n_test = (df["datetime"] >= cutoff).sum()
    print(f"rows={len(df)}  train={len(df) - n_test}  test={n_test} (test เริ่ม {cutoff.date()})")
    print(df.groupby("gym_name")["count"].agg(["mean", "max"]).round(1))


if __name__ == "__main__":
    main()