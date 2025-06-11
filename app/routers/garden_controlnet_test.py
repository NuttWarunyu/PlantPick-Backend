from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import os, io, base64, time, requests
from datetime import datetime

router = APIRouter()

def image_to_base64(img: Image.Image) -> str:
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

@router.post("/test-garden")
async def test_garden(
    image: UploadFile = File(...),
    prompt: str = Form(...)
):
    timestamp = datetime.now().strftime("%H:%M:%S")

    try:
        image_bytes = await image.read()
        original_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_b64 = image_to_base64(original_img)

        payload = {
            "version": "922c7bb67b87ec32cbc2fd11b1d5f94f0ba4f5519c4dbd02856376444127cc60",
            "input": {
                "image": f"data:image/png;base64,{image_b64}",
                "prompt": prompt,
                "num_samples": "1",
                "image_resolution": "512",
                "detect_resolution": 512,
                "ddim_steps": 20,
                "scale": 9,
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

        for attempt in range(45):
            poll = requests.get(prediction_url, headers=headers).json()
            print(f"[{timestamp}] Poll attempt {attempt+1}: status = {poll['status']}")

            if poll["status"] == "succeeded":
                return {"status": "success", "result_url": poll["output"]}
            elif poll["status"] == "failed":
                return JSONResponse(status_code=500, content={"error": "Prediction failed"})

            time.sleep(3)

        return JSONResponse(status_code=504, content={"error": "Prediction timed out"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})