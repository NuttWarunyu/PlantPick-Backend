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
                    f"Based on this garden design prompt: '{prompt}', suggest a list of materials "
                    f"with material_name, quantity, estimated_cost (in USD, max 2 decimal places), and affiliate_link. "
                    f"Use only these materials: trees, flowers, pathways, fountains, stones, planting soil, lawn. "
                    f"Return ONLY a valid JSON array, no explanation, no markdown."
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
                material_name=item.get("material_name", "Unknown"),
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
        "Analyze this garden image and suggest a list of materials with material_name, quantity, "
        "estimated_cost (in USD, max 2 decimal places), and affiliate_link. "
        "Use only these materials: trees, flowers, pathways, fountains, stones, planting soil, lawn. "
        "Return ONLY a valid JSON array, no explanation, no markdown."
    )
    if budget:
        prompt += f" Ensure the total estimated_cost does not exceed {budget} USD."

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
        # ตรวจสอบและแก้ไข JSON ที่ไม่สมบูรณ์
        if not raw_response.startswith('['):
            raw_response = '[' + raw_response
        if not raw_response.endswith(']'):
            raw_response = raw_response.rstrip(',') + ']'
        bom_data = json.loads(raw_response)

        if not isinstance(bom_data, list):
            bom_data = [bom_data]

        total_cost = sum(item.get("estimated_cost", 0.0) for item in bom_data)
        print(f"💵 Total estimated cost: {total_cost} USD | Budget: {budget if budget else 'None'}")

        if budget and total_cost > budget:
            print("⚠️ Cost exceeds budget. Falling back to budget-based suggestion.")
            return analyze_bom_from_budget(budget)

        return [
            BOMItem(
                material_name=item.get("material_name", "Unknown"),
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
            return analyze_bom_from_budget(budget)
        return default_bom_fallback(budget)
    except Exception as e:
        print(f"❌ General Error parsing BOM from image: {str(e)}")
        print(f"📄 Raw response:\n{raw_response}")
        return default_bom_fallback(budget)

def analyze_bom_from_budget(budget: float) -> List[BOMItem]:
    MATERIAL_CATALOG = [
    {"material_name": "ทางเดิน", "unit_price": 30000},
    {"material_name": "ไม้ประธาน", "unit_price": 15000},
    {"material_name": "ต้นพุ่ม", "unit_price": 250},
    {"material_name": "ไม้ดอก", "unit_price": 120},
    {"material_name": "สนามหญ้า", "unit_price": 90},
    {"material_name": "หินตกแต่ง", "unit_price": 80},
    {"material_name": "น้ำพุ", "unit_price": 20000},
    {"material_name": "วัสดุปลูก", "unit_price": 150},
]

    catalog_str = "\n".join([f"- {item['material_name']} (ราคาเฉลี่ย: {item['unit_price']} บาท)" for item in MATERIAL_CATALOG])

    prompt = f"""
        คุณเป็นนักออกแบบสวนที่เชี่ยวชาญ

        ลูกค้าต้องการจัดสวนโดยใช้งบประมาณไม่เกิน {budget} บาท กรุณาแนะนำวัสดุและอุปกรณ์ที่จำเป็น โดยเลือกจากวัสดุที่กำหนดไว้ด้านล่าง และคำนวณราคาโดยรวมทั้งหมดต้องไม่เกินงบประมาณที่ให้

        **วัสดุที่เลือกได้:**
        {catalog_str}

        **รูปแบบผลลัพธ์ที่ต้องการ:**
        - แสดงชื่อวัสดุเป็นภาษาไทย
        - ระบุจำนวน (`quantity`) และ `estimated_cost` เป็นจำนวนเงินบาท (จำนวนเต็มหรือทศนิยมไม่เกิน 2 ตำแหน่ง)        
        - ระบุลิงก์สินค้าใน `affiliate_link`
        - ส่งกลับเป็น JSON array เท่านั้น พร้อมฟิลด์ `"total_estimated_cost"` ที่เป็นผลรวมของราคาทั้งหมด
        - ห้ามมีข้อความอธิบายอื่นใดนอกเหนือจาก JSON

        **ตัวอย่าง:**
        ```json
        [
        {{
            "material_name": "ไม้ประธาน",
            "quantity": 2,
            "estimated_cost": 30000,
            "affiliate_link": "https://example.com/tree"
        }},
        ...
        ],
        "total_estimated_cost": 98950
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
                material_name=item.get("material_name", "Unknown"),
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
        return [BOMItem(material_name="วัสดุปลูก", quantity=10, estimated_cost=min(150.00, budget/10), affiliate_link="https://shopee.co.th/dirt")]
    return [BOMItem(material_name="วัสดุปลูก", quantity=10, estimated_cost=150.00, affiliate_link="https://shopee.co.th/dirt")]