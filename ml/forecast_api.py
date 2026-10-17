"""
API พยากรณ์ความหนาแน่น (ฝั่ง A) ตามสัญญาใน API.md

  GET /gyms/{gym_id}/forecast?date=YYYY-MM-DD       พยากรณ์รายชั่วโมงของวันนั้น
  GET /gyms/{gym_id}/now?at=YYYY-MM-DDTHH:MM        ประมาณจำนวนคน ณ เวลานี้ (at ไม่บังคับ ใช้จำลองเวลาตอนเดโม)

รันทดสอบเดี่ยวๆ (จากโฟลเดอร์รากของโปรเจกต์):
    uvicorn ml.forecast_api:app --reload
แล้วเปิด http://127.0.0.1:8000/docs

ฝั่ง B นำไปรวมกับแอปหลักได้โดย:
    from ml.forecast_api import router
    app.include_router(router)
"""
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ml.current import forecast_now
from ml.forecast import forecast_day


class HourForecast(BaseModel):
    hour: int
    predicted_count: int
    predicted_pct: float
    level: str


class ForecastResponse(BaseModel):
    gym_id: int
    date: str
    model: str
    hours: list[HourForecast]


class NowResponse(BaseModel):
    gym_id: int
    capacity: int
    at: str
    hour: int
    model: str
    is_open: bool
    predicted_count: int
    predicted_pct: float
    level: str  # low / medium / high / closed


router = APIRouter()

NO_MODEL = "ยังไม่มีไฟล์โมเดล ให้รัน python ml/train_models.py ก่อน"


@router.get("/gyms/{gym_id}/forecast", response_model=ForecastResponse)
def get_forecast(gym_id: int, date: dt.date | None = None):
    """พยากรณ์รายชั่วโมงของยิม gym_id ในวันที่ date (YYYY-MM-DD) ถ้าไม่ส่งมาใช้วันนี้"""
    day = date or dt.date.today()
    try:
        return forecast_day(gym_id, day.isoformat())
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=NO_MODEL)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"ไม่พบ gym_id={gym_id}")


@router.get("/gyms/{gym_id}/now", response_model=NowResponse)
def get_now(gym_id: int, at: dt.datetime | None = None):
    """ประมาณจำนวนคนในยิม ณ เวลานี้ (เวลาไทย) ถ้าส่ง at จะใช้เวลานั้นแทน (ไว้จำลองตอนเดโม)"""
    try:
        return forecast_now(gym_id, at)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=NO_MODEL)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"ไม่พบ gym_id={gym_id}")


# แอปสำหรับทดสอบฝั่ง A เอง (ฝั่ง B ใช้ router ของตัวเองได้)
app = FastAPI(title="Gym occupancy forecast API (part A)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ตอนพัฒนาให้หน้าเว็บต่างพอร์ตเรียกได้
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)