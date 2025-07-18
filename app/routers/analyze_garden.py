from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import openai
import os
import base64
import io
from PIL import Image
from dotenv import load_dotenv
import re
import json

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

router = APIRouter()

@router.post("/garden/analyze-garden")
async def analyze_garden(image: UploadFile = File(...)):
    """
    รับรูปสวนจริง วิเคราะห์จุดเด่น/จุดอ่อน/แสง/ลม ด้วย OpenAI
    คืน insight/suggestions (array ของ string ภาษาไทย)
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY ยังไม่ถูกตั้งค่า")
    try:
        # อ่านไฟล์ + ย่อขนาด
        image_bytes = await image.read()
        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((300, 300))
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            "คุณเป็นนักจัดสวนมืออาชีพ ช่วยวิเคราะห์ภาพสวนนี้และให้ insight/ข้อเสนอแนะในรูปแบบ JSON array ภาษาไทยเท่านั้น (ห้ามมีข้อความอื่นนอกจาก JSON array):\n"
            "- วิเคราะห์จุดอ่อน จุดแข็ง จุดอับแสง จุดแดดจัด จุดลมแรง\n"
            "- แนะนำพรรณไม้หรือการปรับปรุงที่เหมาะสมกับแต่ละจุด\n"
            "- ข้อเสนอแนะควรสั้น กระชับ ตรงประเด็น\n"
            "ตัวอย่าง: [\"ควรเพิ่มไม้พุ่มกันลมบริเวณขอบรั้วทิศตะวันตก\", \"มุมซ้ายของสวนได้รับแสงแดดจัด เหมาะกับไม้ดอก\"]"
        )
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "วิเคราะห์สวนนี้"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=400
        )
        raw_response = response.choices[0].message.content
        # ลบ Markdown Syntax (```json ... ```)
        cleaned = re.sub(r"^```json\\s*|\\s*```$", "", raw_response or "", flags=re.MULTILINE).strip()
        try:
            suggestions = json.loads(cleaned)
        except Exception:
            suggestions = [cleaned]
        return {"suggestions": suggestions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)}) 