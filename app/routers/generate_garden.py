from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from PIL import Image
import os, io, base64, time, requests
from datetime import datetime
import redis
from sqlalchemy.orm import Session
from typing import List # <-- Import List สำหรับ Type Hinting

# Import โมเดลทั้งหมดที่เราต้องใช้
from app.database import SessionLocal, GenerationHistory, BOMDetail, GardenRequest, Material, Vendor, Product
from supabase import create_client, Client
from .analyze_bom import analyze_bom_from_image, BOMItem
from pydantic import BaseModel
import logging

# (โค้ดส่วน logging, router, clients, get_db, และฟังก์ชันจัดการรูปภาพ เหมือนเดิม)
# ...
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = APIRouter()
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


# === จุดแก้ไขที่ 1: อัปเดตฟังก์ชัน generate_garden ให้รับข้อมูลใหม่ ===
@router.post("/generate-garden")
async def generate_garden(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    # รับ selected_tags มาเป็น List ของ string
    selected_tags: List[str] = Form(...), 
    ref_code: str = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_ip = request.client.host
    user_agent = request.headers.get("user-agent")
    logger.info(f"[{timestamp}] 🔍 New request from {user_ip} - Tags: {selected_tags}")

    # (โค้ดส่วนจัดการ limit และการสร้างภาพกับ Replicate เหมือนเดิมทั้งหมด)
    # ...
    key = f"ip:{user_ip}:daily_limit"
    try:
        daily_used = int(redis_client.get(key) or 0)
    except redis.RedisError as e:
        return JSONResponse(status_code=500, content={"error": f"Redis error: {str(e)}"})
    share_bonus = 5 if ref_code and redis_client.get(f"ref:{ref_code}:claimed") else 0
    total_limit = 300 + share_bonus
    if daily_used >= total_limit:
        raise HTTPException(status_code=403, detail=f"Daily limit of {total_limit} exceeded")
    try:
        image_bytes = await image.read()
        original_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        original_img = resize_image(original_img)
        image_b64 = image_to_base64(original_img)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Image processing error: {str(e)}"})
    payload = {
        "version": "922c7bb67b87ec32cbc2fd11b1d5f94f0ba4f5519c4dbd02856376444127cc60",
        "input": { "image": f"data:image/png;base64,{image_b64}", "prompt": prompt, "num_samples": "1", "image_resolution": "512", "detect_resolution": 512, "ddim_steps": 10, "scale": 7.5, "a_prompt": "best quality, extremely detailed, photorealistic garden design", "n_prompt": "lowres, bad anatomy, blurry, unrealistic" }
    }
    headers = { "Authorization": f"Token {os.getenv('REPLICATE_API_TOKEN')}", "Content-Type": "application/json" }
    response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers)
    if response.status_code != 201:
        return JSONResponse(status_code=500, content={"error": "Replicate request failed", "details": response.text})
    prediction_url = response.json()["urls"]["get"]
    # ...

    for attempt in range(30):
        poll = requests.get(prediction_url, headers=headers).json()
        if poll["status"] == "succeeded":
            correct_url = poll["output"][1] if len(poll["output"]) > 1 else poll["output"][0]

            try:
                redis_client.set(key, daily_used + 1)
                redis_client.expire(key, 24 * 3600)
            except redis.RedisError as e:
                return JSONResponse(status_code=500, content={"error": f"Redis update error: {str(e)}"})

            try:
                # === จุดแก้ไขที่ 2: บันทึก selected_tags ลงในฐานข้อมูล ===
                new_request = GenerationHistory(
                    ip=user_ip,
                    prompt=prompt,
                    image_url=correct_url,
                    created_at=datetime.now(),
                    ddim_steps=10,
                    user_agent=user_agent,
                    selected_tags=selected_tags # <-- บันทึกแท็กที่ผู้ใช้เลือกลง DB
                )
                db.add(new_request)
                db.commit()
            except Exception as e:
                db.rollback()
                return JSONResponse(status_code=500, content={"error": f"Database error: {str(e)}"})

            return {
                "status": "success",
                "result_url": correct_url,
                "remaining": total_limit - (daily_used + 1),
                "history_id": new_request.history_id
            }

        elif poll["status"] == "failed":
            return JSONResponse(status_code=500, content={"error": "Prediction failed"})

        time.sleep(3)

    return JSONResponse(status_code=504, content={"error": "Prediction timed out"})


# === จุดแก้ไขที่ 3: อัปเดต BOMRequest model ให้รับ budget_level ===
class BOMRequest(BaseModel):
    history_id: int
    budget: float
    budget_level: int # <-- เพิ่มฟิลด์สำหรับรับระดับงบประมาณ

@router.post("/generate-bom")
async def generate_bom(req: BOMRequest, db: Session = Depends(get_db)):
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == req.history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")

    # === จุดแก้ไขที่ 4: อัปเดต budget_level ในประวัติ ===
    try:
        history.budget_level = req.budget_level
        db.commit()
        logger.info(f"Updated history_id {req.history_id} with budget_level {req.budget_level}")
    except Exception as e:
        db.rollback()
        logger.error(f"Could not update budget_level for history_id {req.history_id}: {e}")
        # ไม่ต้องหยุดการทำงาน ให้ทำต่อไปได้

    try:
        bom_items = analyze_bom_from_image(req.history_id, history.image_url, db, budget=req.budget)
        logger.info(f"Marketplace BOM items generated: {bom_items}")
    except Exception as e:
        logger.error(f"Unexpected error in BOM analysis: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})

    bom_details_for_frontend = [item.model_dump() for item in bom_items]
    total_cost = sum(item["estimated_cost"] for item in bom_details_for_frontend)

    # (โค้ดส่วนบันทึก BOM log และการ return เหมือนเดิม)
    # ...
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
    # ...

    return {
        "status": "success",
        "total_cost": total_cost,
        "bom_details": bom_details_for_frontend
    }


# (ฟังก์ชัน upload_image เหมือนเดิม)
@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        filename = f"{int(time.time())}_{file.filename}"
        supabase.storage.from_("generated-gardens").upload(file=contents, path=filename, file_options={"content-type": file.content_type})
        public_url = supabase.storage.from_("generated-gardens").get_public_url(filename)
        return {"status": "success", "url": public_url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Upload failed: {str(e)}"})
