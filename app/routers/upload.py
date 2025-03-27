from fastapi import APIRouter, UploadFile, File
import openai
import os
import base64
import io
from PIL import Image

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@router.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    try:
        # อ่านไฟล์ + ย่อขนาด
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        image = image.resize((300, 300))

        # แปลงภาพเป็น base64
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # เรียกใช้ OpenAI API
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a plant identification expert."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Identify the plant in this image."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=500
        )

        plant_name = response.choices[0].message.content.strip()
        return {"plant_name": plant_name}

    except Exception as e:
        return {"error": str(e)}