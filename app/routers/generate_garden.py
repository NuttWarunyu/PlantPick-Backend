from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from PIL import Image  # เปลี่ยนจาก Image, ImageResampling
import os, io, base64, time, requests
from datetime import datetime
import redis
from sqlalchemy.orm import Session
from app.database import SessionLocal, UsageLimit, GenerationHistory, BOMDetail, GardenRequest
from supabase import create_client, Client

router = APIRouter()

# Redis setup with Railway environment
redis_url = os.getenv("REDIS_URL")  # Railway จะให้ REDIS_URL
if redis_url:
    redis_client = redis.from_url(redis_url)
else:
    redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)), db=0)

# Supabase Storage setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Convert image to base64 string
def image_to_base64(img: Image.Image) -> str:
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# Resize image (optional optimization)
def resize_image(img: Image.Image, size: int = 512) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)  # ใช้ Image.Resampling

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
    print(f"[{timestamp}] 🔍 New request from {user_ip} - Prompt: {prompt}")

    # Check daily limit
    key = f"ip:{user_ip}:daily_limit"
    try:
        daily_used = int(redis_client.get(key) or 0)
        print(f"[{timestamp}] 📊 Redis daily usage for IP {user_ip}: {daily_used}")
    except redis.RedisError as e:
        print(f"[{timestamp}] ❌ Redis error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Redis error: {str(e)}"})

    share_bonus = 5 if ref_code and redis_client.get(f"ref:{ref_code}:claimed") else 0
    total_limit = 3 + share_bonus
    if daily_used >= total_limit:
        print(f"[{timestamp}] 🚫 Daily limit exceeded ({daily_used}/{total_limit})")
        raise HTTPException(status_code=403, detail=f"Daily limit of {total_limit} exceeded")

    # Process image
    try:
        image_bytes = await image.read()
        original_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        original_img = resize_image(original_img)
        image_b64 = image_to_base64(original_img)
        print(f"[{timestamp}] 🖼️ Image processed and converted to base64")
    except Exception as e:
        print(f"[{timestamp}] ❌ Image processing error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Image processing error: {str(e)}"})

    # Send to Replicate
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
        print(f"[{timestamp}] ❌ Replicate request failed: {response.text}")
        return JSONResponse(status_code=500, content={"error": "Replicate request failed", "details": response.text})

    prediction_url = response.json()["urls"]["get"]
    print(f"[{timestamp}] ⏳ Prediction started: {prediction_url}")

    for attempt in range(30):
        poll = requests.get(prediction_url, headers=headers).json()
        print(f"[{timestamp}] Poll attempt {attempt+1}: status = {poll['status']}")

        if poll["status"] == "succeeded":
            correct_url = poll["output"][1] if len(poll["output"]) > 1 else poll["output"][0]
            print(f"[{timestamp}] ✅ Prediction succeeded. Image URL: {correct_url}")

            # Update Redis usage
            try:
                redis_client.set(key, daily_used + 1)
                redis_client.expire(key, 24 * 3600)
                print(f"[{timestamp}] 🔄 Redis usage updated for {user_ip}")
            except redis.RedisError as e:
                print(f"[{timestamp}] ❌ Redis update error: {str(e)}")
                return JSONResponse(status_code=500, content={"error": f"Redis update error: {str(e)}"})

            # Save to DB
            try:
                history = GenerationHistory(
                    ip=user_ip,
                    image_url=correct_url,
                    prompt=prompt,
                    created_at=datetime.now(),
                    ddim_steps=10,
                    user_agent=user_agent
                )
                db.add(history)
                db.commit()
                print(f"[{timestamp}] 🗂️ History saved with ID: {history.history_id}")
            except Exception as e:
                db.rollback()
                print(f"[{timestamp}] ❌ Database error: {str(e)}")
                return JSONResponse(status_code=500, content={"error": f"Database error: {str(e)}"})

            return {
                "status": "success",
                "result_url": correct_url,
                "remaining": total_limit - (daily_used + 1),
                "history_id": history.history_id
            }

        elif poll["status"] == "failed":
            print(f"[{timestamp}] ❌ Prediction failed")
            return JSONResponse(status_code=500, content={"error": "Prediction failed"})

        time.sleep(3)

    print(f"[{timestamp}] ⏰ Prediction timed out after 30 attempts")
    return JSONResponse(status_code=504, content={"error": "Prediction timed out"})

# WARM UP ENDPOINT
@router.get("/ping-replicate")
async def ping_replicate():
    """Ping the model on Replicate to keep it warm without generating real images."""
    dummy_image = Image.new("RGB", (64, 64), (255, 255, 255))
    image_b64 = image_to_base64(dummy_image)

    try:
        payload = {
            "version": "922c7bb67b87ec32cbc2fd11b1d5f94f0ba4f5519c4dbd02856376444127cc60",
            "input": {
                "image": f"data:image/png;base64,{image_b64}",
                "prompt": "Ping test to keep model warm",
                "num_samples": "1",
                "image_resolution": "256",
                "detect_resolution": 256,
                "ddim_steps": 1,
                "scale": 1,
                "a_prompt": "",
                "n_prompt": ""
            }
        }

        headers = {
            "Authorization": f"Token {os.getenv('REPLICATE_API_TOKEN')}",
            "Content-Type": "application/json"
        }

        response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers)
        if response.status_code != 201:
            return JSONResponse(status_code=500, content={"error": "Replicate ping failed", "details": response.text})

        prediction_url = response.json()["urls"]["get"]

        for _ in range(2):
            poll = requests.get(prediction_url, headers=headers).json()
            if poll["status"] == "succeeded" or poll["status"] == "processing":
                return {"status": "ping sent"}

            time.sleep(1)

        return JSONResponse(status_code=202, content={"status": "ping sent but not confirmed"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Endpoint สำหรับ BOM
@router.post("/generate-bom")
async def generate_bom(history_id: int = Form(...), db: Session = Depends(get_db)):
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")

    # สมมติสร้าง BOM (จะขยาย AI ทีหลัง)
    bom = BOMDetail(
        history_id=history_id,
        material_name="ดินปลูกต้นไม้",
        quantity=10,
        estimated_cost=5.00,
        affiliate_link="https://shopee.co.th/dirt",
        created_at=datetime.now()
    )
    db.add(bom)
    db.commit()
    return {"status": "success", "bom_id": bom.bom_id}

# Endpoint สำหรับแจ้งจัดสวน
@router.post("/request-garden")
async def request_garden(
    history_id: int = Form(...),
    budget: float = Form(...),
    location: str = Form(...),
    additional_details: str = Form(None),
    db: Session = Depends(get_db)
):
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")

    request = GardenRequest(
        history_id=history_id,
        budget=budget,
        location=location,
        additional_details=additional_details,
        status="pending",
        created_at=datetime.now(),
        fee_charged=5.00
    )
    db.add(request)
    db.commit()
    return {"status": "success", "request_id": request.request_id}

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