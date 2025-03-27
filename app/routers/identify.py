import openai
import base64
import io
import os
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File
from PIL import Image

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY ยังไม่ถูกตั้งค่า")

router = APIRouter()

@router.post("/identify/")
async def analyze_image(file: UploadFile = File(...)):
    try:
        print("Starting image analysis...")
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        image = image.resize((300, 300))

        print("Converting image to base64...")
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        print("Creating OpenAI client...")
        client = openai.OpenAI(api_key=OPENAI_API_KEY, proxies=None)
        print("Client created successfully")

        print("Calling OpenAI API...")
        response = client.chat.completions.create(
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

        print("API call successful")
        result = response.choices[0].message.content.strip()
        return {"plant_info": result}

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return {"error": str(e)}