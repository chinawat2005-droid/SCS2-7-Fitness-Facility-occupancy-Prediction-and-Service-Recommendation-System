"""ตัวเปิดแอปรวม: ใช้แอปของส่วน A (app.main) เหมือนเดิม แล้วเสียบ Dashboard ของส่วน B เข้าไป
ไม่แก้ไฟล์ของส่วน A เลย"""
from pathlib import Path

from fastapi.responses import FileResponse

from .main import app          # แอปของเพื่อน (ไม่แตะ)
from .dashboard import router as dashboard_router

PAGE = Path(__file__).resolve().parent.parent / "frontend" / "dashboard.html"


def _dashboard_page():
    return FileResponse(PAGE)


# เพิ่ม route ของเรา แล้วย้ายไปไว้ข้างหน้าสุด
# กันกรณีแอปของเพื่อน mount static ที่ "/" ไว้ แล้วดักทุก path ก่อน
_before = len(app.router.routes)
app.include_router(dashboard_router)
app.add_api_route("/dashboard-page", _dashboard_page, include_in_schema=False)
app.router.routes[:] = app.router.routes[_before:] + app.router.routes[:_before]
