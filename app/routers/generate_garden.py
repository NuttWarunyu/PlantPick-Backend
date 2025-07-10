from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, Path
from fastapi.responses import JSONResponse
from PIL import Image
import os, io, base64, time, requests
from datetime import datetime
import redis
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal, GenerationHistory, BOMDetail
from supabase import create_client, Client
from .analyze_bom import analyze_bom_from_image, BOMItem
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# (โค้ดส่วน Clients, get_db, และฟังก์ชันจัดการรูปภาพ เหมือนเดิม)
# ...
redis_url = os.getenv("REDIS_URL")
if redis_url:
    redis_client = redis.from_url(redis_url)
else:
    redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)), db=0)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def image_to_base64(img: Image.Image) -> str:
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
def resize_image(img: Image.Image, size: int = 512) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)
# ...

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_API_HEADERS = {
    "Authorization": f"Token {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json"
}

# === จุดแก้ไขที่ 1: Endpoint `/generate-garden` ใหม่ (Fire and Forget) ===
@router.post("/generate-garden")
async def generate_garden(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    selected_tags: List[str] = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user_ip = request.client.host
    logger.info(f"🔍 New generation request from {user_ip} - Tags: {selected_tags}")

    # (โค้ดส่วนจัดการ limit เหมือนเดิม)
    key = f"ip:{user_ip}:daily_limit"
    daily_used = int(redis_client.get(key) or 0)
    if daily_used >= 300: # สมมติว่าลิมิตคือ 300
        raise HTTPException(status_code=403, detail="Daily limit exceeded")

    try:
        image_bytes = await image.read()
        image_b64 = image_to_base64(resize_image(Image.open(io.BytesIO(image_bytes)).convert("RGB")))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Image processing error: {str(e)}"})

    payload = {
        "version": "922c7bb67b87ec32cbc2fd11b1d5f94f0ba4f5519c4dbd02856376444127cc60",
        "input": { "image": f"data:image/png;base64,{image_b64}", "prompt": prompt }
    }

    # ส่งคำสั่งไป Replicate
    response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=REPLICATE_API_HEADERS)
    if response.status_code != 201:
        return JSONResponse(status_code=500, content={"error": "Replicate request failed", "details": response.text})

    prediction_data = response.json()
    prediction_id = prediction_data.get("id")

    # บันทึกประวัติเบื้องต้นพร้อม prediction_id
    try:
        new_request = GenerationHistory(
            ip=user_ip,
            prompt=prompt,
            selected_tags=selected_tags,
            replicate_prediction_id=prediction_id, # <-- บันทึก ID การทำนาย
            created_at=datetime.now(),
            user_agent=request.headers.get("user-agent")
        )
        db.add(new_request)
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": f"Database error: {str(e)}"})

    # ส่ง "บัตรคิว" กลับไปให้ Frontend ทันที
    return {"status": "processing", "prediction_id": prediction_id}


# === จุดแก้ไขที่ 2: Endpoint ใหม่สำหรับเช็คสถานะ (Polling) ===
@router.get("/check-prediction/{prediction_id}")
async def check_prediction(prediction_id: str = Path(...), db: Session = Depends(get_db)):
    prediction_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    
    try:
        response = requests.get(prediction_url, headers=REPLICATE_API_HEADERS)
        response.raise_for_status()
        poll_data = response.json()
        status = poll_data.get("status")

        if status == "succeeded":
            # หาประวัติที่ตรงกับ prediction_id
            history = db.query(GenerationHistory).filter(GenerationHistory.replicate_prediction_id == prediction_id).first()
            if not history:
                raise HTTPException(status_code=404, detail="Original generation history not found.")

            # อัปเดต image_url ในประวัติ
            result_url = poll_data["output"][1] if len(poll_data["output"]) > 1 else poll_data["output"][0]
            history.image_url = result_url
            db.commit()
            
            # เพิ่มการนับ limit หลังจากสำเร็จ
            key = f"ip:{history.ip}:daily_limit"
            daily_used = int(redis_client.get(key) or 0)
            redis_client.set(key, daily_used + 1, ex=24 * 3600)

            return {
                "status": "succeeded",
                "result_url": result_url,
                "history_id": history.history_id
            }
        elif status == "failed":
            return {"status": "failed", "error": poll_data.get("error")}
        else:
            return {"status": "processing"}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to poll Replicate: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


# (Endpoint /generate-bom และ /upload-image เหมือนเดิม ไม่มีการเปลี่ยนแปลง)
class BOMRequest(BaseModel):
    history_id: int
    budget: float
    budget_level: int

@router.post("/generate-bom")
async def generate_bom(req: BOMRequest, db: Session = Depends(get_db)):
    # ... (โค้ดส่วนนี้เหมือนเดิม)
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == req.history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    try:
        history.budget_level = req.budget_level
        db.commit()
        logger.info(f"Updated history_id {req.history_id} with budget_level {req.budget_level}")
    except Exception as e:
        db.rollback()
        logger.error(f"Could not update budget_level for history_id {req.history_id}: {e}")
    try:
        bom_items = analyze_bom_from_image(req.history_id, history.image_url, db, budget=req.budget)
        logger.info(f"Marketplace BOM items generated: {bom_items}")
    except Exception as e:
        logger.error(f"Unexpected error in BOM analysis: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})
    bom_details_for_frontend = [item.model_dump() for item in bom_items]
    total_cost = sum(item["estimated_cost"] for item in bom_details_for_frontend)
    try:
        for item in bom_items:
            bom_db_entry = BOMDetail(
                history_id=req.history_id,
                material_name=f"{item.material_name} (from {item.vendor_name})",
                quantity=item.quantity,
                estimated_cost=item.estimated_cost,
                affiliate_link=item.product_url or "",
                created_at=datetime.now()
            )
            db.add(bom_db_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Could not save BOM history to bom_details table: {e}")
    return {
        "status": "success",
        "total_cost": total_cost,
        "bom_details": bom_details_for_frontend
    }
# ...

