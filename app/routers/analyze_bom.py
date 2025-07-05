from typing import List, Optional
from pydantic import BaseModel
import os
from openai import OpenAI
from sqlalchemy.orm import Session
from app.database import BOMDetail, GenerationHistory
import requests
from PIL import Image
import io
import base64
import json
import re

class BOMItem(BaseModel):
    material_name: str
    quantity: int
    estimated_cost: float
    affiliate_link: str

def clean_openai_response(raw_response: str) -> str:
    cleaned = re.sub(r"```(?:json)?|```", "", raw_response).strip()
    if not cleaned.startswith('['):
        cleaned = '[' + cleaned
    if not cleaned.endswith(']'):
        cleaned = cleaned.rstrip(',') + ']'
    return cleaned

def analyze_bom(history_id: int, prompt: str, db: Session) -> List[BOMItem]:
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == history_id).first()
    if not history:
        raise ValueError("History not found")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": (
                    f"จากคำอธิบายการออกแบบสวนนี้: '{prompt}' กรุณาแนะนำรายการวัสดุ "
                    f"ที่มี material_name, quantity, estimated_cost (ในหน่วยบาทไทย, ทศนิยมสูงสุด 2 ตำแหน่ง), และ affiliate_link. "
                    f"ใช้เฉพาะวัสดุจากรายการที่กำหนดในตารางด้านล่างตามสไตล์สวนที่ระบุใน prompt. "
                    f"ส่งกลับเป็น JSON array ที่ถูกต้องเท่านั้น ไม่ต้องมีคำอธิบายหรือ markdown."
                )
            }
        ],
        max_tokens=300
    )

    try:
        raw_response = response.choices[0].message.content
        print("🧠 Raw response from OpenAI (text prompt):\n", raw_response)
        raw_response = clean_openai_response(raw_response)
        bom_data = json.loads(raw_response)
        if not isinstance(bom_data, list):
            bom_data = [bom_data]

        return [
            BOMItem(
                material_name=item.get("material_name", "ไม่ระบุ"),
                quantity=item.get("quantity", 1),
                estimated_cost=float(item.get("estimated_cost", 0.0)),
                affiliate_link=item.get("affiliate_link", "")
            )
            for item in bom_data
        ]
    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error parsing BOM from prompt: {str(e)}")
        print(f"📄 Raw response:\n{raw_response}")
        return default_bom_fallback()
    except Exception as e:
        print(f"❌ General Error parsing BOM from prompt: {str(e)}")
        print(f"📄 Raw response:\n{raw_response}")
        return default_bom_fallback()

def analyze_bom_from_image(history_id: int, image_url: str, db: Session, budget: Optional[float] = None) -> List[BOMItem]:
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == history_id).first()
    if not history:
        raise ValueError("History not found")

    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as e:
        raise ValueError(f"Failed to load image from {image_url}: {str(e)}")

    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = (
        "วิเคราะห์ภาพสวนนี้และแนะนำรายการวัสดุที่มี material_name, quantity, "
        "estimated_cost (ในหน่วยบาทไทย, ทศนิยมสูงสุด 2 ตำแหน่ง), และ affiliate_link. "
        "ใช้เฉพาะวัสดุจากรายการที่กำหนดในตารางด้านล่างตามสไตล์สวนที่ระบุใน prompt. "
        "ส่งกลับเป็น JSON array ที่ถูกต้องเท่านั้น ไม่ต้องมีคำอธิบายหรือ markdown."
    )
    if budget:
        prompt += f" ตรวจสอบให้แน่ใจว่าราคารวมทั้งหมดไม่เกิน {budget} บาท."

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                ]
            }
        ],
        max_tokens=400
    )

    try:
        raw_response = response.choices[0].message.content
        print("🧠 Raw response from OpenAI (image prompt):\n", raw_response)
        raw_response = clean_openai_response(raw_response)
        if not raw_response.startswith('['):
            raw_response = '[' + raw_response
        if not raw_response.endswith(']'):
            raw_response = raw_response.rstrip(',') + ']'
        bom_data = json.loads(raw_response)

        if not isinstance(bom_data, list):
            bom_data = [bom_data]

        total_cost = sum(item.get("estimated_cost", 0.0) for item in bom_data)
        print(f"💵 Total estimated cost: {total_cost} บาท | Budget: {budget if budget else 'None'}")

        if budget and total_cost > budget:
            print("⚠️ Cost exceeds budget. Falling back to budget-based suggestion.")
            return analyze_bom_from_budget(budget, prompt)  # ส่ง prompt ไปด้วย

        return [
            BOMItem(
                material_name=item.get("material_name", "ไม่ระบุ"),
                quantity=item.get("quantity", 1),
                estimated_cost=float(item.get("estimated_cost", 0.0)),
                affiliate_link=item.get("affiliate_link", "")
            )
            for item in bom_data
        ]

    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error parsing BOM from image: {str(e)}")
        print(f"📄 Raw response:\n{raw_response}")
        if budget:
            print("🔁 Falling back to budget-based analysis...")
            return analyze_bom_from_budget(budget, prompt)  # ส่ง prompt ไปด้วย
        return default_bom_fallback(budget)
    except Exception as e:
        print(f"❌ General Error parsing BOM from image: {str(e)}")
        print(f"📄 Raw response:\n{raw_response}")
        return default_bom_fallback(budget)

def analyze_bom_from_budget(budget: float, prompt: str = "") -> List[BOMItem]:
    # รายการวัสดุตามตารางที่ล็อกไว้
    MATERIAL_CATALOG = {
        "english": [
            {"material_name": "กุหลาบ", "unit_price": 1200},
            {"material_name": "พยับหมอก", "unit_price": 600},
            {"material_name": "เดซี่", "unit_price": 500},
            {"material_name": "โรสแมรี่", "unit_price": 300},
            {"material_name": "ต้นนีออน", "unit_price": 400},
            {"material_name": "สนมังกร", "unit_price": 250},
            {"material_name": "สนฉัตร", "unit_price": 250},
        ],
        "tropical": [
            {"material_name": "ปาล์ม", "unit_price": 1500},
            {"material_name": "บานบุรี", "unit_price": 800},
            {"material_name": "เฮเลโคนีย์", "unit_price": 700},
            {"material_name": "เฟินใบมะขาม", "unit_price": 350},
            {"material_name": "เอื้องหมายนา", "unit_price": 600},
            {"material_name": "ต้นคล้า", "unit_price": 400},
            {"material_name": "ไอริช", "unit_price": 300},
        ],
        "japanese": [
            {"material_name": "โบนไซ", "unit_price": 2000},
            {"material_name": "ไผ่", "unit_price": 800},
            {"material_name": "ต้นสนญี่ปุ่น", "unit_price": 1500},
            {"material_name": "สนใบพาย", "unit_price": 400},
            {"material_name": "มอส", "unit_price": 400},
            {"material_name": "หลิวลู่ลม", "unit_price": 500},
            {"material_name": "ไอริส", "unit_price": 600},
        ]
    }

    # ตรวจสอบสไตล์จาก prompt โดยใช้ regex
    style = "english"  # Default
    if "tropical" in prompt.lower():
        style = "tropical"
    elif "japanese" in prompt.lower():
        style = "japanese"
    elif "english" in prompt.lower():
        style = "english"

    catalog = MATERIAL_CATALOG[style]

    catalog_str = "\n".join([f"- {item['material_name']} (ราคาเฉลี่ย: {item['unit_price']} บาท)" for item in catalog])

    prompt = f"""
        คุณเป็นนักออกแบบสวนที่เชี่ยวชาญ

        ลูกค้าต้องการจัดสวนสไตล์ {style} โดยใช้งบประมาณไม่เกิน {budget} บาท กรุณาแนะนำวัสดุและอุปกรณ์ที่จำเป็น โดยเลือกจากวัสดุที่กำหนดไว้ด้านล่าง และคำนวณราคาโดยรวมทั้งหมดต้องไม่เกินงบประมาณที่ให้

        **วัสดุที่เลือกได้:**
        {catalog_str}

        **รูปแบบผลลัพธ์ที่ต้องการ:**
        - แสดงชื่อวัสดุเป็นภาษาไทย
        - ระบุจำนวน (`quantity`) และ `estimated_cost` เป็นจำนวนเงินบาท (จำนวนเต็มหรือทศนิยมไม่เกิน 2 ตำแหน่ง)        
        - ระบุลิงก์สินค้าใน `affiliate_link`
        - ส่งกลับเป็น JSON array เท่านั้น พร้อมฟิลด์ `\"total_estimated_cost\"` ที่เป็นผลรวมของราคาทั้งหมด
        - ห้ามมีข้อความอธิบายอื่นใดนอกเหนือจาก JSON

        **ตัวอย่าง:**
        ```json
        [
            {{
                \"material_name\": \"กุหลาบ\",
                \"quantity\": 2,
                \"estimated_cost\": 2400,
                \"affiliate_link\": \"https://example.com/rose\"
            }},
            ...
        ],
        \"total_estimated_cost\": 98950
        ตอบเป็น JSON array อย่างเดียว ห้ามมีคำอธิบายหรือ markdown
        """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400
    )

    try:
        raw_response = response.choices[0].message.content
        print("🧠 Raw response from OpenAI (budget fallback):\n", raw_response)
        raw_response = clean_openai_response(raw_response)

        total_match = re.search(r'"total_estimated_cost"\s*:\s*(\d+(\.\d+)?)', raw_response)
        total_cost = float(total_match.group(1)) if total_match else 0.0
        raw_json = re.sub(r',?\s*"total_estimated_cost"\s*:\s*\d+(\.\d+)?', "", raw_response)

        bom_data = json.loads(raw_json)
        if not isinstance(bom_data, list):
            bom_data = [bom_data]

        return [
            BOMItem(
                material_name=item.get("material_name", "ไม่ระบุ"),
                quantity=item.get("quantity", 1),
                estimated_cost=float(item.get("estimated_cost", 0.0)),
                affiliate_link=item.get("affiliate_link", "")
            )
            for item in bom_data
        ]
    except json.JSONDecodeError as e:
            print(f"❌ JSON Decode Error parsing BOM from budget fallback: {str(e)}")
            print(f"📄 Raw response:\n{raw_response}")
            return default_bom_fallback(budget)
    except Exception as e:
            print(f"❌ General Error parsing BOM from budget fallback: {str(e)}")
            print(f"📄 Raw response:\n{raw_response}")
            return default_bom_fallback(budget)

def default_bom_fallback(budget: Optional[float] = None) -> List[BOMItem]:
    if budget:
        return [BOMItem(material_name="ดินปลูก", quantity=10, estimated_cost=min(150.00, budget/10), affiliate_link="https://shopee.co.th/dirt")]
    return [BOMItem(material_name="ดินปลูก", quantity=10, estimated_cost=150.00, affiliate_link="https://shopee.co.th/dirt")]