"""
สร้างชุดรีวิวภาษาไทยจำลอง (ติดป้าย Sentiment + ประเด็น) สำหรับฝึกโมดูลวิเคราะห์รีวิว
ใช้: python gen_reviews.py   (รันจากโฟลเดอร์รากของโปรเจกต์)
ผลลัพธ์: data/reviews_synthetic.csv

ป้าย sentiment:  pos / neu / neg   (ประโยคที่มีทั้งชมและติ = neu)
ประเด็น (aspects): equipment, cleanliness, air_conditioning, staff, service, crowding, price

หมายเหตุ: รีวิวชุดนี้ประกอบจากเทมเพลต ใช้ "ฝึก" เท่านั้น
ชุด "ทดสอบ" คือ data/reviews_manual.csv ที่เขียนและตรวจป้ายด้วยมือ
"""
import random
from pathlib import Path

import pandas as pd

SEED = 7
N = 300

ASPECTS = {
    "equipment": {
        "pos": ["เครื่องครบทุกส่วน", "อุปกรณ์ใหม่สภาพดีมาก", "ดัมเบลล์น้ำหนักครบ",
                "เครื่องเวทเยอะดี", "เครื่องวิ่งใหม่เอี่ยม"],
        "neg": ["เครื่องเสียบ่อยมาก", "อุปกรณ์เก่าสนิมขึ้น", "เครื่องเวทน้อยเกินไป",
                "เครื่องวิ่งพังหลายเครื่อง", "บาร์เบลมีไม่พอ"],
        "neu": ["เครื่องมีทั้งคาร์ดิโอกับเวท", "อุปกรณ์ก็แบบทั่วไป", "เครื่องมีให้เลือกพอสมควร"],
    },
    "cleanliness": {
        "pos": ["สะอาดมาก", "ห้องน้ำสะอาดไม่มีกลิ่น", "พื้นสะอาดเช็ดเครื่องทุกชั่วโมง",
                "ห้องอาบน้ำสะอาดน่าใช้"],
        "neg": ["ห้องน้ำสกปรกมาก", "มีกลิ่นอับทั้งห้อง", "พื้นเปียกลื่นไม่มีคนเช็ด",
                "เครื่องเหงื่อเกรอะไม่มีใครเช็ด"],
        "neu": ["ความสะอาดก็ปกติ", "ห้องน้ำโอเคตามมาตรฐาน"],
    },
    "air_conditioning": {
        "pos": ["แอร์เย็นฉ่ำ", "แอร์เย็นสบายตลอด", "อากาศถ่ายเทดี"],
        "neg": ["แอร์ไม่เย็นเลย", "ร้อนอบอ้าวมาก", "แอร์เสียบ่อย", "อากาศอึดอัดไม่ถ่ายเท"],
        "neu": ["แอร์เย็นพอใช้", "อุณหภูมิก็ปานกลาง"],
    },
    "staff": {
        "pos": ["พนักงานน่ารักมาก", "เทรนเนอร์ใจดีแนะนำดี", "พนักงานต้อนรับดียิ้มแย้ม",
                "พี่ๆ ช่วยดูท่าให้ฟรี"],
        "neg": ["พนักงานพูดจาไม่ดี", "พนักงานไม่สนใจลูกค้า", "เทรนเนอร์เอาแต่เล่นมือถือ",
                "พนักงานตอบช้าและหน้าบึ้ง"],
        "neu": ["พนักงานก็ปกติ", "เทรนเนอร์มีให้จ้างแยก"],
    },
    "service": {
        "pos": ["บริการดีมีน้ำดื่มฟรี", "ระบบจองใช้ง่าย", "เปิดปิดตรงเวลา", "มีผ้าเช็ดตัวให้"],
        "neg": ["ระบบจองคิวค้างบ่อย", "แจ้งปัญหาไปก็ไม่มีใครแก้", "ไม่มีผ้าเช็ดตัวให้",
                "ที่จอดรถไม่พอ"],
        "neu": ["บริการก็มาตรฐาน", "มีที่จอดรถพอใช้"],
    },
    "crowding": {
        "pos": ["คนไม่เยอะสบายมาก", "ไม่ต้องรอเครื่อง", "ช่วงเช้าเงียบดี"],
        "neg": ["ช่วงเย็นคนแน่นมาก", "ต้องรอเครื่องนานมาก", "คนเยอะเกินไปแย่งกันใช้เครื่อง"],
        "neu": ["คนมีบ้างบางช่วง", "ช่วงเย็นคนเริ่มเยอะ"],
    },
    "price": {
        "pos": ["ราคาถูกคุ้มมาก", "ค่าสมาชิกไม่แพง", "โปรโมชั่นดีมาก"],
        "neg": ["ราคาแพงเกินไป", "ค่าสมาชิกแพงเมื่อเทียบกับของที่ได้", "ขึ้นราคาบ่อยไม่คุ้ม"],
        "neu": ["ราคากลางๆ", "ราคาพอๆ กับที่อื่น"],
    },
}

ENDS = {
    "pos": ["ชอบมาก", "แนะนำเลย", "ประทับใจ", "จะมาอีกแน่นอน"],
    "neg": ["ไม่แนะนำ", "ผิดหวังมาก", "เสียดายเงิน", "ไม่มาอีกแล้ว"],
    "neu": ["เฉยๆ", "ก็ใช้ได้", "ไม่ดีไม่แย่"],
}
SAME = [" ", " และ", " อีกทั้ง"]       # เชื่อมประโยคที่ความรู้สึกเหมือนกัน
CONTRAST = [" แต่", " แต่ว่า", " ส่วน"]  # เชื่อมประโยคที่ความรู้สึกต่างกัน
SUFFIX = ["", "", "", "!", "!!", " จริงๆ", " เลย"]


def build_review(rng):
    n = rng.choices([1, 2, 3], [0.40, 0.45, 0.15])[0]
    keys = rng.sample(list(ASPECTS), n)
    pols = [rng.choices(["pos", "neg", "neu"], [0.40, 0.35, 0.25])[0] for _ in keys]

    text = rng.choice(ASPECTS[keys[0]][pols[0]])
    for i in range(1, n):
        link = CONTRAST if pols[i] != pols[i - 1] else SAME
        text += rng.choice(link) + rng.choice(ASPECTS[keys[i]][pols[i]])

    has_pos, has_neg = "pos" in pols, "neg" in pols
    label = "pos" if (has_pos and not has_neg) else "neg" if (has_neg and not has_pos) else "neu"
    if rng.random() < 0.5:
        text += " " + rng.choice(ENDS[label])
    text += rng.choice(SUFFIX)

    rating = {"pos": rng.choice([4, 5]), "neu": 3, "neg": rng.choice([1, 2])}[label]
    order = list(ASPECTS)
    aspects = ";".join(sorted(keys, key=order.index))
    return text, label, aspects, rating


def main():
    rng = random.Random(SEED)
    rows, seen = [], set()
    tries = 0
    while len(rows) < N and tries < 20 * N:
        tries += 1
        text, label, aspects, rating = build_review(rng)
        if text in seen:
            continue
        seen.add(text)
        rows.append(dict(review_id=len(rows) + 1, text=text, sentiment=label,
                         aspects=aspects, rating=rating, source="synthetic"))

    df = pd.DataFrame(rows)
    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/reviews_synthetic.csv", index=False, encoding="utf-8-sig")
    print(f"สร้างรีวิว {len(df)} ข้อความ -> data/reviews_synthetic.csv")
    print(df["sentiment"].value_counts().to_string())


if __name__ == "__main__":
    main()