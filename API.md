# API Contract (ล็อกวันที่ 16 ต.ค. — ห้ามเปลี่ยนชื่อฟิลด์โดยไม่บอกอีกฝั่ง)

Base URL (ตอนพัฒนา): `http://localhost:8000`
รูปแบบข้อมูล: JSON, วันที่ `YYYY-MM-DD`, ชั่วโมง 0-23, `level` เป็นหนึ่งใน `low | medium | high`
เกณฑ์ level: low < 35%, medium < 65%, high >= 65% (นิยามเดียวกับ `gen_occupancy_data.py`)

ผู้รับผิดชอบ: **A** = ข้อมูล/โมเดล, **B** = เว็บ/ฐานข้อมูล

## ตารางฐานข้อมูล

| ตาราง | ฟิลด์ |
|---|---|
| gyms | gym_id (PK), name, capacity, lat, lng, equipment, facilities, open_weekday, open_weekend |
| occupancy | gym_id, datetime, date, hour, day_of_week, is_weekend, is_holiday, is_exam_period, count, capacity, occupancy_pct, level |
| users | user_id (PK), username, password_hash, role (user/owner/admin) |
| reviews | review_id (PK), gym_id, user_id, rating (1-5), text, created_at, sentiment (pos/neu/neg), aspects (เช่น "equipment;cleanliness") |
| issues | issue_id (PK), gym_id, review_id, status (open/fixed/confirmed), updated_at |

`equipment` และ `facilities` เก็บเป็นข้อความคั่นด้วย `;` ตามไฟล์ CSV

## Endpoints

### 1) GET /gyms  — B
รายการยิม พร้อมระดับความหนาแน่น ณ ปัจจุบัน (ใช้ข้อมูลชั่วโมงล่าสุดในฐานข้อมูลสำหรับเดโม)
Query (ไม่บังคับ): `lat`, `lng` ถ้าส่งมาจะคำนวณ `distance_km`

```json
[
  {
    "gym_id": 2,
    "name": "Mega Gym",
    "lat": 16.445,
    "lng": 102.835,
    "capacity": 120,
    "equipment": ["treadmill", "cable", "free_weights"],
    "facilities": ["locker", "shower"],
    "open_weekday": "06:00-23:00",
    "open_weekend": "07:00-21:00",
    "current_count": 84,
    "current_pct": 70.0,
    "current_level": "high",
    "distance_km": 1.8,
    "avg_rating": 4.2
  }
]
```

### 2) GET /gyms/{gym_id}/forecast?date=YYYY-MM-DD  — A (B เรียกใช้)
พยากรณ์รายชั่วโมงของวันนั้น เฉพาะชั่วโมงที่ยิมเปิด

```json
{
  "gym_id": 2,
  "date": "2026-10-20",
  "model": "RandomForest",
  "hours": [
    {"hour": 6, "predicted_count": 26, "predicted_pct": 21.7, "level": "low"},
    {"hour": 18, "predicted_count": 95, "predicted_pct": 79.2, "level": "high"}
  ]
}
```

### 3) POST /recommend  — A
รับตำแหน่งผู้ใช้และความต้องการ ส่งอันดับยิม (และช่วงเวลาที่ดีที่สุด)

Request:
```json
{
  "lat": 16.47,
  "lng": 102.82,
  "date": "2026-10-20",
  "hour": 18,
  "need_equipment": ["squat_rack"],
  "prefer_quiet": true
}
```

Response:
```json
{
  "results": [
    {
      "gym_id": 4,
      "name": "Bon Fitness (KKU)",
      "score": 0.82,
      "distance_km": 0.6,
      "predicted_level": "medium",
      "best_hours": [15, 16],
      "reasons": ["ใกล้คุณ 0.6 กม.", "ช่วง 18:00 คาดว่าคนปานกลาง", "คะแนนรีวิว 4.1"]
    }
  ]
}
หมายเหตุ: คะแนนรวมคิดจาก ความหนาแน่นที่พยากรณ์ (0.35) + ระยะทาง (0.30) + อุปกรณ์ที่ต้องการ (0.20) + คะแนนรีวิว (0.15)
ถ้าไม่มีข้อมูลรีวิว จะตัดปัจจัยนั้นออกแล้วปรับน้ำหนักที่เหลือ `predicted_level` เป็น low / medium / high / closed
ฝั่ง B เรียกใช้ใน Python ได้: `from ml.recommend import recommend` (ส่ง `ratings={gym_id: avg}` ได้)
```

### 4) GET /gyms/{gym_id}/reviews  — B
```json
[
  {
    "review_id": 10,
    "rating": 4,
    "text": "เครื่องใหม่ แต่แอร์ไม่ค่อยเย็นตอนเย็น",
    "created_at": "2026-10-12T19:30:00",
    "sentiment": "neu",
    "aspects": ["equipment", "air_conditioning"]
  }
]
```

### 5) POST /gyms/{gym_id}/reviews  — B (เรียกโมดูล sentiment ของ A)
Request: `{"user_id": 1, "rating": 4, "text": "..."}`
Response: รีวิวที่บันทึกแล้ว (รูปแบบเดียวกับข้อ 4) พร้อม `sentiment` และ `aspects`

### 6) POST /nlp/analyze  — A
ฟังก์ชัน Python ที่ B import ใช้ตรงๆ ก็ได้ (`analyze(text) -> dict`) ไม่จำเป็นต้องเป็น HTTP
Request: `{"text": "พนักงานดี แต่ห้องน้ำสกปรก"}`
Response: `{"sentiment": "neu", "aspects": ["staff", "cleanliness"]}`

aspect ที่ใช้: `equipment`, `cleanliness`, `air_conditioning`, `staff`, `service`, `crowding`, `price`

### 7) GET /owner/dashboard?gym_id=2  — B (ข้อมูลสรุปจาก A)
```json
{
  "gym_id": 2,
  "avg_rating": 4.2,
  "sentiment_counts": {"pos": 40, "neu": 12, "neg": 8},
  "aspect_counts": {"equipment": 25, "cleanliness": 14},
  "peak_hours_weekday": [18, 19],
  "open_issues": 3
}
```

### 8) Issues (ทำแบบย่อ)  — B
- `GET /gyms/{gym_id}/issues`
- `POST /issues/{issue_id}/status` body `{"status": "fixed"}` (owner) หรือ `{"status": "confirmed"}` (user)

## กติกาการทำงานร่วมกัน

1. เปลี่ยนชื่อฟิลด์/รูปแบบ response ต้องแจ้งอีกฝั่งและแก้ไฟล์นี้ในคอมมิตเดียวกัน
2. ระหว่างรอฝั่ง A ทำเสร็จ B ใช้ mock response ตามตัวอย่างข้างบนได้เลย
3. push ทุกคืน คนละ branch แล้วรวมเข้า `main` เมื่อผ่านการทดสอบเอง
4. feature freeze: วันที่ 22 ต.ค. เวลา 11:00 หลังจากนั้นแก้บั๊กเท่านั้น
