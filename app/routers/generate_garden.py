from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, Path, Query
from fastapi.responses import JSONResponse
from PIL import Image
import os
import io
import base64
import time
import requests
from datetime import datetime
import redis
from sqlalchemy.orm import Session
from typing import List
import httpx

from app.database import SessionLocal, GenerationHistory, BOMDetail, GardenRequest
from supabase import create_client, Client
from .analyze_bom import analyze_bom_from_image, BOMItem
from .shopee import get_shopee_products # <-- Import ฟังก์ชันจาก shopee.py
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# (โค้ดส่วน Clients, get_db, และฟังก์ชันจัดการรูปภาพ เหมือนเดิม)
# ... (ส่วนนี้ไม่มีการเปลี่ยนแปลง)
redis_url = os.getenv("REDIS_URL")
if redis_url:
    redis_client = redis.from_url(redis_url)
else:
    redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)), db=0)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE is not set in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
def get_db():
    db = SessionLocal();
    try: yield db
    finally: db.close()
def image_to_base64(img: Image.Image) -> str:
    buffered = io.BytesIO(); img.save(buffered, format="PNG"); return base64.b64encode(buffered.getvalue()).decode("utf-8")
def resize_with_aspect_ratio(img: Image.Image, max_size: int = 1024) -> Image.Image:
    width, height = img.size; aspect_ratio = width / height
    if width > height: new_width = max_size; new_height = int(new_width / aspect_ratio)
    else: new_height = max_size; new_width = int(new_height * aspect_ratio)
    new_width -= (new_width % 8); new_height -= (new_height % 8)
    logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION")
REPLICATE_API_HEADERS = {"Authorization": f"Token {REPLICATE_API_TOKEN}", "Content-Type": "application/json"}
# ... (จบส่วนที่ไม่มีการเปลี่ยนแปลง)

# === ฟังก์ชันอัปโหลดไฟล์ไป Supabase Storage ด้วย httpx (async) ===
async def upload_to_supabase(file_bytes: bytes, file_name: str, content_type: str = "image/png"):
    SUPABASE_URL = "https://ejcieklcwkhrkcxcfhxx.supabase.co"
    SUPABASE_BUCKET = "generated-images"
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

    # ใส่ print debug ตรงนี้
    print(f"[DEBUG] SUPABASE_KEY: {SUPABASE_KEY[:8]}...{SUPABASE_KEY[-8:]}" if SUPABASE_KEY else "[DEBUG] SUPABASE_KEY: None")

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{file_name}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(upload_url, content=file_bytes, headers=headers)

    if response.status_code in [200, 201]:
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{file_name}"
        print(f"[DEBUG] Supabase upload success: {public_url}")
        return public_url
    else:
        print(f"[DEBUG] Upload failed: {response.status_code}, {response.text}")
        raise Exception(f"Upload failed: {response.status_code}, {response.text}")


# (Endpoint /generate-garden, /check-prediction, /generate-bom เหมือนเดิม)
# ... (ส่วนนี้ไม่มีการเปลี่ยนแปลง)
@router.post("/generate-garden")
async def generate_garden(
    request: Request,
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    prompt: str = Form(...),
    selected_tags: List[str] = Form(...),
    db: Session = Depends(get_db)
):
    if not REPLICATE_MODEL_VERSION: raise HTTPException(status_code=500, detail="REPLICATE_MODEL_VERSION is not set.")
    user_ip = request.client.host if request.client else "unknown"; logger.info(f"🎨 New Garden Generation request from {user_ip}")
    key = f"ip:{user_ip}:daily_limit"
    value = redis_client.get(key)
    if value is not None:
        if isinstance(value, bytes):
            daily_used = int(value.decode())
        elif isinstance(value, (int, str)):
            daily_used = int(value)
        else:
            daily_used = 0
    else:
        daily_used = 0
    if daily_used >= 300: raise HTTPException(status_code=403, detail="Daily limit exceeded")
    try:
        original_bytes = await image.read()
        # อัปโหลดภาพต้นฉบับ (ใช้ httpx)
        original_file_name = f"original/user_{int(time.time())}.png"
        try:
            print("[DEBUG] Before upload_to_supabase")
            original_url = await upload_to_supabase(original_bytes, original_file_name, content_type="image/png")
            print("[DEBUG] After upload_to_supabase")
        except Exception as e:
            print(f"[DEBUG] Exception before/after upload: {e}")
            raise
        # โหลดใหม่เป็น BytesIO เพื่อใช้กับ PIL
        original_image = Image.open(io.BytesIO(original_bytes)).convert("RGB")
        mask_image = Image.open(io.BytesIO(await mask.read())).convert("L")
        resized_image = resize_with_aspect_ratio(original_image, max_size=1024)
        resized_mask = mask_image.resize(resized_image.size, Image.Resampling.LANCZOS)
        image_b64 = image_to_base64(resized_image)
        mask_b64 = image_to_base64(resized_mask)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Image processing error: {str(e)}"})
    standard_negative_prompt = "blurry, low quality, cartoon, unrealistic, deformed, watermark, text, signature, ugly, distorted"
    payload = {"version": REPLICATE_MODEL_VERSION, "input": {"image": f"data:image/png;base64,{image_b64}", "mask": f"data:image/png;base64,{mask_b64}", "prompt": prompt, "negative_prompt": standard_negative_prompt}}
    try:
        response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=REPLICATE_API_HEADERS); response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Replicate API request failed: {e.response.text}"); return JSONResponse(status_code=500, content={"error": "Replicate request failed", "details": e.response.json() if "application/json" in e.response.headers.get("Content-Type", "") else e.response.text})
    prediction_id = response.json().get("id")
    try:
        new_request = GenerationHistory(ip=user_ip, prompt=prompt, selected_tags=selected_tags, replicate_prediction_id=prediction_id, created_at=datetime.now(), user_agent=request.headers.get("user-agent")); db.add(new_request); db.commit()
    except Exception as e: db.rollback(); return JSONResponse(status_code=500, content={"error": f"Database error: {str(e)}"})
    return {"status": "processing", "prediction_id": prediction_id}

@router.get("/check-prediction/{prediction_id}")
async def check_prediction(prediction_id: str = Path(...), db: Session = Depends(get_db)):
    prediction_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    try:
        response = requests.get(prediction_url, headers=REPLICATE_API_HEADERS); response.raise_for_status(); poll_data = response.json(); assert isinstance(poll_data, dict)
        status = poll_data.get("status")
        if status == "succeeded":
            history = db.query(GenerationHistory).filter(GenerationHistory.replicate_prediction_id == prediction_id).first()
            if not history: raise HTTPException(status_code=404, detail="Original generation history not found.")
            # ดาวน์โหลดภาพที่ gen เสร็จจาก replicate แล้วอัปโหลดเข้า Supabase (ใช้ httpx)
            gen_url_from_replicate = poll_data["output"][1] if len(poll_data["output"]) > 1 else poll_data["output"][0]
            try:
                gen_img_response = requests.get(gen_url_from_replicate)
                gen_img_response.raise_for_status()
                gen_file_name = f"gen/{history.ip}_{int(time.time())}.png"
                generated_url = await upload_to_supabase(gen_img_response.content, gen_file_name, content_type="image/png")
            except Exception as e:
                logger.error(f"Failed to upload generated image to Supabase: {e}")
                generated_url = gen_url_from_replicate  # fallback
            setattr(history, "image_url", generated_url)
            db.commit()
            key = f"ip:{history.ip}:daily_limit"
            value = redis_client.get(key)
            if value is not None:
                if isinstance(value, bytes):
                    daily_used = int(value.decode())
                elif isinstance(value, (int, str)):
                    daily_used = int(value)
                else:
                    daily_used = 0
            else:
                daily_used = 0
            redis_client.set(key, daily_used + 1, ex=24 * 3600)
            return {"status": "succeeded", "result_url": generated_url, "history_id": history.history_id}
        elif status == "failed": return {"status": "failed", "error": poll_data.get("error")}
        else: return {"status": "processing"}
    except requests.exceptions.RequestException as e: raise HTTPException(status_code=502, detail=f"Failed to poll Replicate: {e}")
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

class BOMRequest(BaseModel):
    history_id: int; budget: float; budget_level: int

@router.post("/generate-bom")
async def generate_bom(req: BOMRequest, db: Session = Depends(get_db)):
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == req.history_id).first()
    if not history: raise HTTPException(status_code=404, detail="History not found")
    try:
        setattr(history, "budget_level", req.budget_level)
    except Exception as e: db.rollback(); logger.error(f"Could not update budget_level for history_id {req.history_id}: {e}")
    try:
        analysis_result = analyze_bom_from_image(req.history_id, history.__dict__["image_url"], db, budget=req.budget)
        logger.info(f"Smart substitution analysis result: {analysis_result}")
    except Exception as e:
        logger.error(f"Unexpected error in BOM analysis: {str(e)}"); return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})
    main_bom_items = analysis_result.get("main_bom", []); suggestions = analysis_result.get("suggestions", {})
    main_bom_details = [item.model_dump() for item in main_bom_items]
    suggestions_details = suggestions
    total_cost = sum(item.estimated_cost for item in main_bom_items)
    try:
        for item in main_bom_items:
            db.add(BOMDetail(history_id=req.history_id, material_name=f"{item.material_name} (from {item.vendor_name})", quantity=item.quantity, estimated_cost=item.estimated_cost, affiliate_link=item.product_url or "", created_at=datetime.now()))
        db.commit()
    except Exception as e: db.rollback(); logger.error(f"Could not save BOM history to bom_details table: {e}")
    return {"status": "success", "total_cost": total_cost, "bom_details": main_bom_details, "suggestions": suggestions_details}
# ... (จบส่วนที่ไม่มีการเปลี่ยนแปลง)


# === จุดแก้ไขที่ 2: สร้าง Endpoint ใหม่สำหรับขอ Affiliate Link ===
@router.get("/get-affiliate-link")
async def get_affiliate_link(item_name: str = Query(...)):
    """
    รับชื่อวัสดุ แล้วไปค้นหาดีลที่ดีที่สุดจาก Shopee Affiliate API
    """
    logger.info(f"🔗 Affiliate link requested for: {item_name}")
    try:
        # เรียกใช้ฟังก์ชันเดิมที่เรามีอยู่แล้วจาก shopee.py
        products = await get_shopee_products(item_name, 0)
        
        if not products:
            logger.warning(f"No Shopee products found for '{item_name}'. Returning generic search link.")
            # ถ้าหาไม่เจอ ให้ส่งลิงก์ค้นหาทั่วไปแทน
            return {"offerLink": f"https://shopee.co.th/search?keyword={item_name}"}
            
        # เลือกสินค้าที่ราคาถูกที่สุดมาเป็นตัวแทน
        best_offer = min(products, key=lambda x: float(x["price"]))
        
        logger.info(f"Found best offer for '{item_name}': {best_offer['offerLink']}")
        # ส่งเฉพาะ offerLink กลับไป
        return {"offerLink": best_offer["offerLink"]}

    except Exception as e:
        logger.error(f"💥 Error getting affiliate link for '{item_name}': {e}")
        # กรณีเกิด Error ก็ส่งลิงก์ค้นหาทั่วไปกลับไป
        return {"offerLink": f"https://shopee.co.th/search?keyword={item_name}"}
