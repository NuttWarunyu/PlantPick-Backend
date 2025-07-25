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
import logging

logger = logging.getLogger(__name__)

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
        logger.error("OPENAI_API_KEY is not set")
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY ยังไม่ถูกตั้งค่า")
    
    logger.info(f"OpenAI API Key check passed - Key: {OPENAI_API_KEY[:10]}...")
    try:
        # อ่านไฟล์ + ย่อขนาด
        image_bytes = await image.read()
        
        # ตรวจสอบว่าไฟล์ไม่ว่าง
        if not image_bytes:
            raise HTTPException(status_code=400, detail="ไฟล์รูปภาพว่างเปล่า")
        
        # ตรวจสอบ content type
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail=f"ไฟล์ไม่ใช่รูปภาพ: {image.content_type}")
        
        logger.info(f"Processing image: {image.filename}, size: {len(image_bytes)} bytes, type: {image.content_type}")
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as img_error:
            logger.error(f"Failed to open image: {img_error}")
            raise HTTPException(status_code=400, detail="ไม่สามารถเปิดไฟล์รูปภาพได้ - ไฟล์อาจเสียหายหรือไม่ใช่รูปภาพ")
        
        img = img.resize((300, 300))
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            "คุณเป็นนักจัดสวนมืออาชีพ ช่วยวิเคราะห์ภาพสวนนี้และให้ insight/ข้อเสนอแนะในรูปแบบ JSON array ภาษาไทยเท่านั้น (ห้ามมีข้อความอื่นนอกจาก JSON array):\n"
            "- วิเคราะห์จุดอ่อน จุดแข็ง จุดอับแสง จุดแดดจัด จุดลมแรง\n"
            "- เน้นวิเคราะห์พื้นที่โล่งๆ พื้นทราย พื้นหญ้าเปล่า ที่ต้องการการปรับปรุง\n"
            "- แนะนำพรรณไม้หรือการปรับปรุงที่เหมาะสมกับแต่ละจุด\n"
            "- ข้อเสนอแนะควรสั้น กระชับ ตรงประเด็น\n"
            "ตัวอย่าง: [\"พื้นที่ทรายด้านหน้าควรเพิ่มไม้พุ่มและไม้ดอก\", \"สนามหญ้าโล่งควรปลูกไม้คลุมดินและไม้ประดับ\"]"
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
        # ลบ Markdown Syntax และ JSON syntax
        cleaned = re.sub(r"^```json\\s*|\\s*```$", "", raw_response or "", flags=re.MULTILINE).strip()
        # ลบ quotes และ brackets ที่ไม่จำเป็น
        cleaned = re.sub(r"^['\"]*\[|['\"]*\]$", "", cleaned).strip()
        cleaned = re.sub(r"['\"]*,\s*['\"]*", ",", cleaned)
        cleaned = re.sub(r"^['\"]*|['\"]*$", "", cleaned)
        
        try:
            # แยกข้อความด้วย comma และทำความสะอาด
            suggestions = [s.strip().strip('"\'') for s in cleaned.split(',') if s.strip()]
            # ลบข้อความที่ว่างหรือมี syntax ผิด
            suggestions = [s for s in suggestions if s and not s.startswith('[') and not s.endswith(']')]
        except Exception:
            suggestions = [cleaned] if cleaned else []
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error in analyze_garden: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"error": f"Internal server error: {str(e)}"}) 