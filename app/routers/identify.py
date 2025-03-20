import openai
import base64
import io
from fastapi import APIRouter, UploadFile, File
from PIL import Image
import os
from dotenv import load_dotenv

load_dotenv()  # โหลดค่าจาก .env

# โหลดค่า API Key จาก Environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ ERROR: OPENAI_API_KEY is not set! Please check your environment variables.")

# ตั้งค่า API Key ให้ OpenAI Client
openai.api_key = OPENAI_API_KEY

# ตั้งค่า Router
router = APIRouter()

def check_base64_size(base64_string: str):
    """ ตรวจสอบขนาดของ Base64 Image """
    return len(base64_string.encode('utf-8'))

@router.post("/identify/")
async def analyze_image(file: UploadFile = File(...)):
    try:
        # อ่านไฟล์ภาพ
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))

        # Resize ให้เล็กลงเพื่อประหยัด Token
        image = image.resize((300, 300))

        # แปลงเป็น Base64
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # ตรวจสอบขนาด Base64
        base64_size = check_base64_size(base64_image)
        if base64_size > 10000:
            return {"error": f"Image is too large. Size: {base64_size} bytes"}

        # ใช้ OpenAI วิเคราะห์รูปภาพ
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "system", "content": "คุณเป็นผู้เชี่ยวชาญในการระบุพืชและต้นไม้จากภาพ"},
                {"role": "user", "content": f"โปรดระบุชื่อพืชในภาพนี้: data:image/jpeg;base64,{base64_image}"}
            ],
            max_tokens=50
        )

        # ดึงผลลัพธ์ชื่อพืชจาก OpenAI
        plant_name = response['choices'][0]['message']['content'].strip()

        return {"plant_name": plant_name}

    except Exception as e:
        return {"error": str(e)}