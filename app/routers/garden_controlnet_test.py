# app/routers/garden_controlnet_test.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import datetime

router = APIRouter()

# ตัวอย่าง schema สำหรับรับข้อมูลทดสอบ
class GardenTestRequest(BaseModel):
    style: Optional[str] = "tropical"  # ตัวอย่างสไตล์สวน
    budget: Optional[float] = 1000.0
    location: Optional[str] = "Bangkok"
    details: Optional[str] = "Test garden design request"

# ตัวอย่าง endpoint ทดสอบ GET
@router.get("/ping")
async def ping():
    return {"message": "pong", "timestamp": datetime.datetime.now().isoformat()}

# ตัวอย่าง endpoint POST สำหรับทดสอบสร้างคำขอสวน
@router.post("/generate")
async def generate_garden(request: GardenTestRequest):
    # แทนที่ด้วยโค้ดจริงที่เรียกโมเดล AI หรือฐานข้อมูล
    response = {
        "status": "success",
        "style": request.style,
        "budget": request.budget,
        "location": request.location,
        "details": request.details,
        "image_url": "https://example.com/generated_garden.png"
    }
    return response