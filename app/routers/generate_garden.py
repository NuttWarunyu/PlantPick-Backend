from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, Path
from fastapi.responses import JSONResponse
from PIL import Image
import os, io, base64, time, requests
from datetime import datetime
import redis
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal, GenerationHistory, BOMDetail, GardenRequest
from supabase import create_client, Client
from .analyze_bom import analyze_bom_from_image
from pydantic import BaseModel
import logging

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
def resize_with_aspect_ratio(img: Image.Image, max_size: int = 1024) -> Image.Image:
    width, height = img.size
    aspect_ratio = width / height
    if width > height:
        new_width = max_size
        new_height = int(new_width / aspect_ratio)
    else:
        new_height = max_size
        new_width = int(new_height * aspect_ratio)
    new_width = new_width - (new_width % 8)
    new_height = new_height - (new_height % 8)
    logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
DEPTH_MODEL_VERSION = os.getenv("REPLICATE_DEPTH_MODEL_VERSION")
INPAINT_MODEL_VERSION = os.getenv("REPLICATE_INPAINT_MODEL_VERSION")

REPLICATE_API_HEADERS = {
    "Authorization": f"Token {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json"
}

@router.post("/generate-garden")
async def generate_garden(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    selected_tags: List[str] = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    if not DEPTH_MODEL_VERSION:
        raise HTTPException(status_code=500, detail="REPLICATE_DEPTH_MODEL_VERSION is not set on the server.")
    user_ip = request.client.host
    logger.info(f"🔍 New 'Inspiration Mode' request from {user_ip}")
    key = f"ip:{user_ip}:daily_limit"
    daily_used = int(redis_client.get(key) or 0)
    if daily_used >= 300:
        raise HTTPException(status_code=403, detail="Daily limit exceeded")
    try:
        image_bytes = await image.read()
        image_b64 = image_to_base64(resize_with_aspect_ratio(Image.open(io.BytesIO(image_bytes)).convert("RGB"), max_size=512))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Image processing error: {str(e)}"})
    payload = {
        "version": DEPTH_MODEL_VERSION,
        "input": { "image": f"data:image/png;base64,{image_b64}", "prompt": prompt }
    }
    response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=REPLICATE_API_HEADERS)
    if response.status_code != 201:
        return JSONResponse(status_code=500, content={"error": "Replicate request failed", "details": response.text})
    prediction_data = response.json()
    prediction_id = prediction_data.get("id")
    try:
        new_request = GenerationHistory(ip=user_ip, prompt=prompt, selected_tags=selected_tags, replicate_prediction_id=prediction_id, created_at=datetime.now(), user_agent=request.headers.get("user-agent"))
        db.add(new_request)
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": f"Database error: {str(e)}"})
    return {"status": "processing", "prediction_id": prediction_id}

@router.post("/generate-inpainting")
async def generate_inpainting(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    prompt: str = Form(...),
    selected_tags: List[str] = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    if not INPAINT_MODEL_VERSION:
        raise HTTPException(status_code=500, detail="REPLICATE_INPAINT_MODEL_VERSION is not set on the server.")
    user_ip = request.client.host
    logger.info(f"🎨 New 'Realistic Mode' request from {user_ip}")
    key = f"ip:{user_ip}:daily_limit"
    daily_used = int(redis_client.get(key) or 0)
    if daily_used >= 300:
        raise HTTPException(status_code=403, detail="Daily limit exceeded")
    try:
        image_bytes = await image.read()
        mask_bytes = await mask.read()
        original_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        mask_image = Image.open(io.BytesIO(mask_bytes)).convert("L")
        resized_image = resize_with_aspect_ratio(original_image, max_size=1024)
        resized_mask = mask_image.resize(resized_image.size, Image.Resampling.LANCZOS)
        image_b64 = image_to_base64(resized_image)
        mask_b64 = image_to_base64(resized_mask)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Image processing error: {str(e)}"})
    payload = {
        "version": INPAINT_MODEL_VERSION,
        "input": {
            "image": f"data:image/png;base64,{image_b64}",
            "mask": f"data:image/png;base64,{mask_b64}",
            "prompt": prompt
        }
    }
    response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=REPLICATE_API_HEADERS)
    response.raise_for_status()
    prediction_data = response.json()
    prediction_id = prediction_data.get("id")
    try:
        new_request = GenerationHistory(ip=user_ip, prompt=prompt, selected_tags=selected_tags, replicate_prediction_id=prediction_id, created_at=datetime.now(), user_agent=request.headers.get("user-agent"))
        db.add(new_request)
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": f"Database error: {str(e)}"})
    return {"status": "processing", "prediction_id": prediction_id}

@router.get("/check-prediction/{prediction_id}")
async def check_prediction(prediction_id: str = Path(...), db: Session = Depends(get_db)):
    prediction_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    try:
        response = requests.get(prediction_url, headers=REPLICATE_API_HEADERS)
        response.raise_for_status()
        poll_data = response.json()
        status = poll_data.get("status")
        if status == "succeeded":
            history = db.query(GenerationHistory).filter(GenerationHistory.replicate_prediction_id == prediction_id).first()
            if not history:
                raise HTTPException(status_code=404, detail="Original generation history not found.")
            result_url = poll_data["output"][1] if len(poll_data["output"]) > 1 else poll_data["output"][0]
            history.image_url = result_url
            db.commit()
            key = f"ip:{history.ip}:daily_limit"
            daily_used = int(redis_client.get(key) or 0)
            redis_client.set(key, daily_used + 1, ex=24 * 3600)
            return {"status": "succeeded", "result_url": result_url, "history_id": history.history_id}
        elif status == "failed":
            return {"status": "failed", "error": poll_data.get("error")}
        else:
            return {"status": "processing"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to poll Replicate: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

class BOMRequest(BaseModel):
    history_id: int
    budget: float
    budget_level: int

@router.post("/generate-bom")
async def generate_bom(req: BOMRequest, db: Session = Depends(get_db)):
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == req.history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    try:
        history.budget_level = req.budget_level
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Could not update budget_level for history_id {req.history_id}: {e}")
    try:
        analysis_result = analyze_bom_from_image(req.history_id, history.image_url, db, budget=req.budget)
        logger.info(f"Smart substitution analysis result: {analysis_result}")
    except Exception as e:
        logger.error(f"Unexpected error in BOM analysis: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})
    main_bom_items = analysis_result.get("main_bom", [])
    suggestions = analysis_result.get("suggestions", {})
    main_bom_details = [item.model_dump() for item in main_bom_items]
    suggestions_details = suggestions
    total_cost = sum(item["estimated_cost"] for item in main_bom_details)
    try:
        for item in main_bom_items:
            db.add(BOMDetail(
                history_id=req.history_id,
                material_name=f"{item.material_name} (from {item.vendor_name})",
                quantity=item['quantity'],
                estimated_cost=item['estimated_cost'],
                affiliate_link=item.get('product_url', ""),
                created_at=datetime.now()
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Could not save BOM history to bom_details table: {e}")
    return {
        "status": "success",
        "total_cost": total_cost,
        "bom_details": main_bom_details,
        "suggestions": suggestions_details
    }

