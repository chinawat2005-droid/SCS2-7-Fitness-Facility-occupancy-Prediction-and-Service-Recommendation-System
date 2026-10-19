import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth import current_user
from app.database import engine
from ml.sentiment import analyze_review

router = APIRouter(tags=["Fitness Reviews"])


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=2, max_length=2000)
    user_id: int | None = None  # รับตาม API contract แต่ไม่เชื่อค่าจาก client


def analyze(text_value):
    try:
        result = analyze_review(text_value)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Sentiment Model ไม่พร้อมใช้งาน"
        ) from exc

    if result.get("sentiment") not in ("pos", "neu", "neg"):
        raise HTTPException(503, "Sentiment ไม่ถูกต้อง")

    aspects = result.get("aspects", [])
    allowed = {
        "equipment", "cleanliness", "air_conditioning",
        "staff", "service", "crowding", "price"
    }
    if not isinstance(aspects, list):
        raise HTTPException(503, "Aspects ไม่ถูกต้อง")

    return result["sentiment"], [
        a for a in aspects if a in allowed
    ]


def serialize(row):
    return {
        "review_id": row["review_id"],
        "rating": row["rating"],
        "text": row["text"],
        "created_at": row["created_at"],
        "sentiment": row["sentiment"],
        "aspects": json.loads(row["aspects"])
    }


@router.get("/gyms/{gym_id}/reviews")
def get_reviews(gym_id: int):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT * FROM reviews
                WHERE gym_id = :gym_id
                ORDER BY review_id DESC
            """),
            {"gym_id": gym_id}
        ).mappings().all()

    return [serialize(row) for row in rows]


@router.post("/gyms/{gym_id}/reviews", status_code=201)
def create_review(
    gym_id: int,
    data: ReviewCreate,
    user: dict = Depends(current_user)
):
    review_text = data.text.strip()

    if len(review_text) < 2:
        raise HTTPException(422, "กรุณาเขียนรีวิวอย่างน้อย 2 ตัวอักษร")

    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT gym_id FROM gyms WHERE gym_id = :i"),
            {"i": gym_id}
        ).first()

    if not exists:
        raise HTTPException(404, "ไม่พบฟิตเนส")

    sentiment, aspects = analyze(review_text)
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO reviews (
                        gym_id, user_id, rating, text,
                        sentiment, aspects, created_at
                    )
                    VALUES (
                        :gym, :user, :rating, :body,
                        :sentiment, :aspects, :created
                    )
                """),
                {
                    "gym": gym_id,
                    "user": user["user_id"],
                    "rating": data.rating,
                    "body": review_text,
                    "sentiment": sentiment,
                    "aspects": json.dumps(aspects, ensure_ascii=False),
                    "created": created_at
                }
            )
            review_id = result.lastrowid
    except IntegrityError as exc:
        raise HTTPException(400, "ไม่สามารถบันทึกรีวิวได้") from exc

    return {
        "review_id": review_id,
        "rating": data.rating,
        "text": review_text,
        "created_at": created_at,
        "sentiment": sentiment,
        "aspects": aspects
    }


@router.get("/gyms/{gym_id}/review-summary")
def review_summary(gym_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT COUNT(*) AS total,
                       AVG(rating) AS average
                FROM reviews
                WHERE gym_id = :gym_id
            """),
            {"gym_id": gym_id}
        ).mappings().one()

    return {
        "gym_id": gym_id,
        "review_count": row["total"],
        "avg_rating": round(row["average"] or 0, 2)
    }
