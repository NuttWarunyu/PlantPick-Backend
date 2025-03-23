import openai
import base64
import io
import os
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File
from PIL import Image

load_dotenv()  # โหลดตัวแปรจาก .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY ยังไม่ถูกตั้งค่า")

openai.api_key = OPENAI_API_KEY

router = APIRouter()

@router.post("/identify/")
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

        # เรียกใช้ gpt-4o vision
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "คุณเป็นผู้เชี่ยวชาญด้านพืช ช่วยระบุชื่อพืชและแนะนำการดูแล"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "ภาพนี้คือต้นอะไร? ช่วยวิเคราะห์ชื่อพืช และระดับการดูแลที่เหมาะสมให้หน่อย"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=500
        )

        result = response['choices'][0]['message']['content'].strip()
        return {"plant_info": result}

    except Exception as e:
        return {"error": str(e)}