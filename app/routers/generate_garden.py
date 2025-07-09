from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from PIL import Image
import os, io, base64, time, requests
from datetime import datetime
import redis
from sqlalchemy.orm import Session
from app.database import SessionLocal, UsageLimit, GenerationHistory, BOMDetail, GardenRequest
from supabase import create_client, Client
# === จุดแก้ไข: ลบการ import ที่ไม่ใช้ออก และ import BOMItem จากไฟล์ใหม่ ===
from .analyze_bom import analyze_bom_from_image, BOMItem
from pydantic import BaseModel
import logging

# ตั้งค่า logging
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

@router.post("/generate-garden")
async def generate_garden(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    ref_code: str = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_ip = request.client.host
    user_agent = request.headers.get("user-agent")
    logger.info(f"[{timestamp}] 🔍 New request from {user_ip} - Prompt: {prompt}")

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
        "input": {
            "image": f"data:image/png;base64,{image_b64}",
            "prompt": prompt,
            "num_samples": "1",
            "image_resolution": "512",
            "detect_resolution": 512,
            "ddim_steps": 10,
            "scale": 7.5,
            "a_prompt": "best quality, extremely detailed, photorealistic garden design",
            "n_prompt": "lowres, bad anatomy, blurry, unrealistic"
        }
    }

    headers = {
        "Authorization": f"Token {os.getenv('REPLICATE_API_TOKEN')}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers)
    if response.status_code != 201:
        return JSONResponse(status_code=500, content={"error": "Replicate request failed", "details": response.text})

    prediction_url = response.json()["urls"]["get"]

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
                new_request = GenerationHistory(
                    ip=user_ip,
                    prompt=prompt,
                    image_url=correct_url,
                    created_at=datetime.now(),
                    ddim_steps=10,
                    user_agent=user_agent
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

class BOMRequest(BaseModel):
    history_id: int
    budget: float

@router.post("/generate-bom")
async def generate_bom(req: BOMRequest, db: Session = Depends(get_db)):
    timestamp = datetime.now().strftime("%H:%M:%S")
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == req.history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")

    try:
        # การเรียกใช้ฟังก์ชันที่ Refactor แล้วยังคงเหมือนเดิม ซึ่งถูกต้องแล้ว
        bom_items = analyze_bom_from_image(req.history_id, history.image_url, db, budget=req.budget)
        logger.info(f"BOM items generated: {bom_items}")
    except ValueError as e:
        return JSONResponse(status_code=500, content={"error": f"BOM analysis failed: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error in BOM analysis: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})

    bom_details = []
    total_cost = 0

    for item in bom_items:
        try:
            # === จุดแก้ไข: เพิ่ม unit_type เข้าไปในการตอบกลับ ===
            # (หมายเหตุ: ตาราง bom_details ยังไม่มีคอลัมน์ unit_type เราจะเพิ่มทีหลัง)
            # ตอนนี้เราจะส่งข้อมูลกลับไปให้ Frontend ก่อน
            bom_details.append({
                "material_name": item.material_name,
                "quantity": item.quantity,
                "unit_type": item.unit_type, # <-- เพิ่มฟิลด์ใหม่
                "estimated_cost": item.estimated_cost,
                "affiliate_link": item.affiliate_link,
            })
            total_cost += float(item.estimated_cost)
            
            # บันทึก BOM ลง DB (เหมือนเดิม)
            bom_db_entry = BOMDetail(
                history_id=req.history_id,
                material_name=item.material_name,
                quantity=item.quantity,
                estimated_cost=item.estimated_cost,
                affiliate_link=item.affiliate_link,
                created_at=datetime.now()
            )
            db.add(bom_db_entry)

        except Exception as e:
            db.rollback()
            logger.error(f"Error processing BOM item: {str(e)}, Item: {vars(item)}")
            return JSONResponse(status_code=500, content={"error": f"Failed to process BOM detail: {str(e)}"})
    
    # Commit การเปลี่ยนแปลงทั้งหมดครั้งเดียวหลังจบ loop
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing BOM details: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Database commit error: {str(e)}"})


    return {
        "status": "success",
        "total_cost": total_cost,
        "bom_details": bom_details
    }

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
