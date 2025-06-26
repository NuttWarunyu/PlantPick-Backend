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


class BOMItem(BaseModel):
    material_name: str
    quantity: int
    estimated_cost: float
    affiliate_link: str


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
                "content": f"Based on this garden design prompt: '{prompt}', suggest a list of materials with material_name, quantity, estimated_cost (in USD, max 2 decimal places), and affiliate_link. Use only these materials: trees, flowers, pathways, fountains, stones, planting soil, lawn. Return in JSON format."
            }
        ],
        max_tokens=300
    )

    try:
        bom_data = json.loads(response.choices[0].message.content)
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
    except Exception as e:
        print(f"Error parsing BOM from prompt: {str(e)}")
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
    prompt = "Analyze this garden image and suggest a list of materials with material_name, quantity, estimated_cost (in USD, max 2 decimal places), and affiliate_link. Use only these materials: trees, flowers, pathways, fountains, stones, planting soil, lawn. Return in JSON format."
    if budget:
        prompt += f" Keep the total estimated_cost within {budget} USD."

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
        max_tokens=300
    )

    try:
        bom_data = json.loads(response.choices[0].message.content)
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
    except Exception as e:
        print(f"Error parsing BOM from image: {str(e)}")
        return default_bom_fallback()


def analyze_bom_from_budget(budget: float) -> List[BOMItem]:
    MATERIAL_CATALOG = [
        {"material_name": "ทางเดิน", "unit": "งาน", "unit_price": 30000},
        {"material_name": "ไม้ประธาน", "unit": "ต้น", "unit_price": 15000},
        {"material_name": "ต้นพุ่ม", "unit": "ต้น", "unit_price": 250},
        {"material_name": "ไม้ดอก", "unit": "ต้น", "unit_price": 120},
        {"material_name": "สนามหญ้า", "unit": "ตร.ม.", "unit_price": 90},
        {"material_name": "หินตกแต่ง", "unit": "ถุง", "unit_price": 80},
        {"material_name": "น้ำพุ", "unit": "ชุด", "unit_price": 20000},
        {"material_name": "วัสดุปลูก", "unit": "ถุง", "unit_price": 150},
    ]

    catalog_str = "\n".join(
        [f"{item['material_name']} ({item['unit']}) - {item['unit_price']} บาท" for item in MATERIAL_CATALOG]
    )

    prompt = f"""
คุณเป็นนักจัดสวน ลูกค้าต้องการจัดสวนโดยใช้งบประมาณไม่เกิน {budget} บาท
วัสดุที่ใช้ได้มีตามนี้:

{catalog_str}

ช่วยเลือกวัสดุที่เหมาะสม พร้อมจำนวน และราคาคร่าวๆ (estimated_cost) โดยตอบกลับเป็น JSON array เท่านั้น เช่น:

[
  {{
    "material_name": "สนามหญ้า",
    "quantity": 50,
    "estimated_cost": 4500,
    "affiliate_link": "https://example.com/lawn"
  }}
]
"""

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400
    )

    try:
        bom_data = json.loads(response.choices[0].message.content)
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
    except Exception as e:
        print(f"Error parsing BOM from budget: {str(e)}")
        return default_bom_fallback()


def default_bom_fallback() -> List[BOMItem]:
    return [
        BOMItem(
            material_name="วัสดุปลูก",
            quantity=10,
            estimated_cost=5.00,
            affiliate_link="https://shopee.co.th/dirt"
        )
    ]