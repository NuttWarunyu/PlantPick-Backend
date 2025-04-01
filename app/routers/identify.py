import openai
import base64
import io
import os
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File
from PIL import Image

# โหลดค่า API Key จาก .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY ยังไม่ถูกตั้งค่า")

router = APIRouter()

@router.post("/identify/")
async def analyze_image(file: UploadFile = File(...)):
    try:
        print("📷 เริ่มวิเคราะห์ภาพ...")
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        image = image.resize((300, 300))  # ลดขนาดเพื่อประหยัด Bandwidth

        # แปลงภาพเป็น Base64
        print("🔄 แปลงรูปเป็น Base64...")
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # ✅ ใช้ OpenAI API Client ตามเวอร์ชันใหม่
        print("🚀 เรียกใช้งาน OpenAI API...")
        client = openai.OpenAI(api_key=OPENAI_API_KEY, proxies=None)


        response = client.chat.completions.create(
             model="gpt-4o",
             messages=[
                {"role": "system", "content": "คุณเป็นผู้เชี่ยวชาญด้านพืช ช่วยระบุชื่อพืชและแนะนำการดูแล"},
                {
            "role": "user",
            "content": [
                {"type": "text", "text": "ภาพนี้คือต้นอะไร?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                  ]
               }
        ],
        max_tokens=500
)

        print("✅ API call successful")
        result = response.choices[0].message.content.strip()
        return {"plant_info": result}

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return {"error": str(e)}