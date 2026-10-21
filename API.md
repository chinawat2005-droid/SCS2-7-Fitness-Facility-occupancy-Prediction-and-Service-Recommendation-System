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
| reviews | review_id (PK), gym_id, user_id (ว่างได้ = รีวิวจำลอง), rating (1-5), text, sentiment (pos/neu/neg), aspects (JSON list เช่น `["equipment","cleanliness"]`), created_at |
| operator_issue_status | gym_id, issue_key (ชื่อ aspect ที่เป็นปัญหา), state (ตารางของ Dashboard ผู้ประกอบการ) |

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
### 2b) GET /gyms/{gym_id}/now  — A
ความหนาแน่นที่พยากรณ์ ณ เวลาปัจจุบัน (เวลาไทย UTC+7) ถ้ายิมปิด `level` เป็น `closed`
Query (ไม่บังคับ): `at=YYYY-MM-DDTHH:MM`

```json
{
  "gym_id": 2,
  "capacity": 120,
  "at": "2026-10-21T17:00:00",
  "hour": 17,
  "model": "RandomForest",
  "is_open": true,
  "predicted_count": 89,
  "predicted_pct": 74.2,
  "level": "high"
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
```
หมายเหตุ: คะแนนรวมคิดจาก ความหนาแน่นที่พยากรณ์ (0.35) + ระยะทาง (0.30) + อุปกรณ์ที่ต้องการ (0.20) + คะแนนรีวิว (0.15) ถ้า `prefer_quiet` เป็นจริง น้ำหนักความหนาแน่นเพิ่มเป็น 0.50 และให้คะแนนแบบยกกำลังสอง
ระบบดึงคะแนนรีวิวเฉลี่ยจากตาราง `reviews` เอง ถ้าไม่มีข้อมูลรีวิว จะตัดปัจจัยนั้นออกแล้วปรับน้ำหนักที่เหลือ ยิมที่ปิดอยู่ได้คะแนน 0 `predicted_level` เป็น low / medium / high / closed

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

### 6) วิเคราะห์รีวิว (Python function)  — A
ไม่มี HTTP endpoint ฝั่ง B เรียกในโค้ด: `from ml.sentiment import analyze_review`
`analyze_review("พนักงานดี แต่ห้องน้ำสกปรก")` คืนค่า
```json
{"sentiment": "neu", "confidence": 0.61, "aspects": ["staff", "cleanliness"]}
```
aspect ที่ใช้: `equipment`, `cleanliness`, `air_conditioning`, `staff`, `service`, `crowding`, `price`

### 7) GET /api/dashboard/summary?gym_id=2  — B
ข้อมูลสรุปสำหรับ Dashboard ผู้ประกอบการ (ใช้ความหนาแน่นจากตาราง occupancy และรีวิวเชิงลบจากตาราง reviews)
```json
{
  "gym_id": 2,
  "gyms": [{"gym_id": 1, "name": "The Boys Gym Club"}],
  "states": ["รอดำเนินการ", "กำลังแก้", "แก้แล้ว"],
  "kpi": {"avg_occupancy_pct": 29.2, "peak_hour": 18, "peak_pct": 69.1, "total_reviews": 40, "open_problems": 8},
  "problems": [
    {"key": "aspect:staff", "title": "รีวิวเชิงลบเรื่องพนักงาน", "count": 6,
     "action": "ทบทวนการดูแลของพนักงาน", "state": "รอดำเนินการ"}
  ],
  "occupancy_by_hour": [{"hour": 18, "pct": 69.1}]
}
```

### 8) POST /api/dashboard/status  — B
ผู้ประกอบการเปลี่ยนสถานะการแก้ปัญหา เก็บในตาราง `operator_issue_status`
Request: `{"gym_id": 2, "issue_key": "aspect:staff", "state": "กำลังแก้"}`
`gym_id` เป็น 0 = ทุกสาขา (ใช้กับ `summary` ที่ไม่ส่ง `gym_id`) `state` เป็นหนึ่งใน `รอดำเนินการ | กำลังแก้ | แก้แล้ว` ถ้าส่งค่าอื่นจะได้ 400
Response: `{"ok": true}`

## กติกาการทำงานร่วมกัน

1. เปลี่ยนชื่อฟิลด์/รูปแบบ response ต้องแจ้งอีกฝั่งและแก้ไฟล์นี้ในคอมมิตเดียวกัน
2. ระหว่างรอฝั่ง A ทำเสร็จ B ใช้ mock response ตามตัวอย่างข้างบนได้เลย
3. push ทุกคืน คนละ branch แล้วรวมเข้า `main` เมื่อผ่านการทดสอบเอง
4. feature freeze: วันที่ 22 ต.ค. เวลา 11:00 หลังจากนั้นแก้บั๊กเท่านั้น
