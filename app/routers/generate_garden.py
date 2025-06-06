from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import base64
import os
import io
import time
import traceback
import requests
from PIL import Image
import numpy as np
import json
from datetime import datetime

router = APIRouter()

# --- Convert image to base64 string ---
def image_to_base64(img: Image.Image) -> str:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔄 Starting image_to_base64: Image size = {img.size}")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    print(f"[{timestamp}] ✅ Completed image_to_base64: Length = {len(base64_str)} bytes")
    return base64_str

# --- Create rectangular mask from bounding box ---
def create_mask_from_bbox(image: Image.Image, bbox: list) -> Image.Image:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔄 Starting create_mask_from_bbox: Image size = {image.size}, Bbox = {bbox}")
    width, height = image.size
    x1 = int(bbox[0] * width)
    y1 = int(bbox[1] * height)
    x2 = int(bbox[2] * width)
    y2 = int(bbox[3] * height)

    mask = Image.new("L", (width, height), 255)  # เริ่มด้วยสีขาว (พื้นหลัง)
    for y in range(y1, y2):
        for x in range(x1, x2):
            mask.putpixel((x, y), 0)

    print(f"[{timestamp}] ✅ Completed create_mask_from_bbox: Mask size = {mask.size}")
    return mask

# --- Generate garden using Replicate API ---
def inpaint_with_replicate(image: Image.Image, mask: Image.Image, prompt: str) -> str:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔄 Starting inpaint_with_replicate: Prompt = {prompt[:50]}...")
    image_b64 = image_to_base64(image)
    mask_b64 = image_to_base64(mask)

    # Debug: ตรวจสอบค่าใน mask
    mask_array = np.array(mask)
    print(f"[{timestamp}] 🖼️ Mask values - Min: {mask_array.min()}, Max: {mask_array.max()}, Unique: {np.unique(mask_array)}")

    headers = {
        "Authorization": f"Token {os.getenv('REPLICATE_API_TOKEN')}",
        "Content-Type": "application/json"
    }
    payload = {
        "version": "a5b13068cc81a89a4fbeefeccc774869fcb34df4dbc92c1555e0f2771d49dde7",
        "input": {
            "image": f"data:image/png;base64,{image_b64}",
            "mask": f"data:image/png;base64,{mask_b64}",
            "prompt": prompt,
            "guidance_scale": 7.5,
            "num_inference_steps": 40,
            "width": image.width,
            "height": image.height
        }
    }

    print(f"[{timestamp}] 📡 Sending request to Replicate API: Payload size = {len(str(payload))}")
    response = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers)
    if response.status_code != 201:
        print(f"[{timestamp}] ❌ Replicate API error (initial): Status = {response.status_code}, Response = {response.text}")
        raise Exception(f"Replicate API error (initial): {response.text}")

    prediction_url = response.json()["urls"]["get"]
    print(f"[{timestamp}] 📤 Prediction URL received: {prediction_url}")

    for i in range(30):
        poll = requests.get(prediction_url, headers=headers)
        poll_data = poll.json()
        print(f"[{timestamp}] 🔁 [{i}] Poll status: {poll_data.get('status')}")
        if poll_data["status"] == "succeeded":
            print(f"[{timestamp}] ✅ Replicate succeeded: Output URL = {poll_data['output']}")
            return poll_data['output']
        elif poll_data["status"] == "failed":
            print(f"[{timestamp}] ❌ Replicate failed: Details = {poll_data}")
            raise Exception(f"Replicate failed: {poll_data}")
        time.sleep(2)

    print(f"[{timestamp}] ⚠️ Replicate generation timed out")
    raise Exception("Replicate generation timed out.")

# --- FastAPI Endpoints ---
@router.post("/generate-garden-mask")
async def generate_garden_realistic(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    prompt: str = Form(...),
    bounding_box: str = Form(None)
):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🚀 Starting /generate-garden-mask: Received image, mask, prompt = {prompt[:50]}..., bbox = {bounding_box}")
    
    try:
        # อ่านภาพและ Mask
        image_bytes = await image.read()
        mask_bytes = await mask.read()
        original_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")  # Grayscale mask

        print(f"[{timestamp}] 📷 Loaded original image: Size = {original_img.size}, Mode = {original_img.mode}")
        print(f"[{timestamp}] 🎭 Loaded mask image: Size = {mask_img.size}, Mode = {mask_img.mode}")

        # Debug: บันทึกภาพต้นฉบับและ Mask
        original_img.save("debug_original_input.png")
        mask_img.save("debug_mask.png")
        print(f"[{timestamp}] 💾 Saved debug images: debug_original_input.png, debug_mask.png")

        # ใช้ Bounding Box ถ้ามี
        final_mask = mask_img
        if bounding_box:
            bbox = json.loads(bounding_box)
            print(f"[{timestamp}] 📐 Parsed bounding box: {bbox}")
            final_mask = create_mask_from_bbox(original_img, bbox)
            final_mask.save("debug_final_mask.png")
            print(f"[{timestamp}] 💾 Saved final mask: debug_final_mask.png")
        else:
            print(f"[{timestamp}] 📏 No bounding box provided, using mask as is.")

        # เตรียม Prompt
        full_prompt = f"A {prompt}, photorealistic style, matching the perspective and lighting of the original image."
        print(f"[{timestamp}] 🧪 Prepared full prompt: {full_prompt}")

        # Inpainting ด้วย Replicate
        image_url = inpaint_with_replicate(original_img, final_mask, full_prompt)
        print(f"[{timestamp}] 🌱 Generated garden image URL: {image_url}")

        return {
            "status": "success",
            "result_url": image_url,
            "prompt": full_prompt
        }

    except Exception as e:
        print(f"[{timestamp}] ❌ ERROR in /generate-garden-mask: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"error": str(e)})