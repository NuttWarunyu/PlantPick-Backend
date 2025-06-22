from typing import List
from pydantic import BaseModel
import os
from openai import OpenAI
from sqlalchemy.orm import Session
from app.database import BOMDetail, GenerationHistory  # Import จาก database.py
import requests
from PIL import Image
import io
import base64

# Model สำหรับ BOM Item
class BOMItem(BaseModel):
    material_name: str
    quantity: int
    estimated_cost: float  # ใช้ float เพื่อเข้ากับ DECIMAL
    affiliate_link: str

# ฟังก์ชันวิเคราะห์ BOM โดยใช้ AI จาก prompt
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
        import json
        bom_data = json.loads(response.choices[0].message.content)
        if not isinstance(bom_data, list):
            bom_data = [bom_data]

        bom_items = []
        for item in bom_data:
            bom_items.append(BOMItem(
                material_name=item.get("material_name", "Unknown"),
                quantity=item.get("quantity", 1),
                estimated_cost=float(item.get("estimated_cost", 0.0)),
                affiliate_link=item.get("affiliate_link", "")
            ))
        return bom_items
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing BOM from prompt: {str(e)}")
        return [
            BOMItem(
                material_name="planting soil",
                quantity=10,
                estimated_cost=5.00,
                affiliate_link="https://shopee.co.th/dirt"
            )
        ]

# ฟังก์ชันวิเคราะห์ BOM จากภาพ
def analyze_bom_from_image(history_id: int, image_url: str, db: Session) -> List[BOMItem]:
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == history_id).first()
    if not history:
        raise ValueError("History not found")

    # ดาวน์โหลดภาพจาก URL
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as e:
        raise ValueError(f"Failed to load image from {image_url}: {str(e)}")

    # แปลงภาพเป็น base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # ใช้ OpenAI Vision API เพื่อวิเคราะห์ภาพ
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",  # ใช้โมเดลที่รองรับ Vision
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this garden image and suggest a list of materials with material_name, quantity, estimated_cost (in USD, max 2 decimal places), and affiliate_link. Use only these materials: trees, flowers, pathways, fountains, stones, planting soil, lawn. Return in JSON format."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                ]
            }
        ],
        max_tokens=300
    )

    try:
        import json
        bom_data = json.loads(response.choices[0].message.content)
        if not isinstance(bom_data, list):
            bom_data = [bom_data]

        bom_items = []
        for item in bom_data:
            bom_items.append(BOMItem(
                material_name=item.get("material_name", "Unknown"),
                quantity=item.get("quantity", 1),
                estimated_cost=float(item.get("estimated_cost", 0.0)),
                affiliate_link=item.get("affiliate_link", "")
            ))
        return bom_items
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing BOM from image: {str(e)}")
        return [
            BOMItem(
                material_name="planting soil",
                quantity=10,
                estimated_cost=5.00,
                affiliate_link="https://shopee.co.th/dirt"
            )
        ]