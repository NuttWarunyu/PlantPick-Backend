from typing import List, Optional, Dict
from pydantic import BaseModel
import os
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import Material
import requests
from PIL import Image
import io
import base64
import json
import re
import random

# ตั้งค่า OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model สำหรับรับส่งข้อมูล BOM
class BOMItem(BaseModel):
    material_name: str
    quantity: int
    unit_type: str
    estimated_cost: float
    affiliate_link: str

# --- ฟังก์ชัน get_materials_from_image เหมือนเดิม ---
def get_materials_from_image(image_b64: str) -> List[str]:
    """ใช้ AI Vision เพื่อลิสต์ชื่อวัสดุที่เห็นในภาพ"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this garden image and list all visible materials like plants, stones, wood, etc. Return only a clean JSON array of strings. For example: [\"Palm Tree\", \"Paving Stone\", \"Wooden Deck\"]. Do not include any explanation."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            max_tokens=200
        )
        raw_response = response.choices[0].message.content
        cleaned_response = re.sub(r"```(?:json)?|```", "", raw_response).strip()
        material_list = json.loads(cleaned_response)
        print(f"🧠 AI identified materials: {material_list}")
        return [str(item) for item in material_list]
    except Exception as e:
        print(f"❌ Error getting materials from image: {e}")
        return []

# --- จุดแก้ไขหลัก: เพิ่ม Debug Log เพื่อดูข้อมูลทั้งหมดใน DB ---
def get_material_details_from_db(material_names: List[str], db: Session) -> List[Dict]:
    """ค้นหารายละเอียดวัสดุจากฐานข้อมูลโดยใช้ชื่อภาษาอังกฤษ (Trimmed, Case-Insensitive & Plural-Insensitive)"""
    if not material_names:
        return []
        
    # === DEBUGGING STEP: แสดงข้อมูลทั้งหมดในตาราง materials ===
    try:
        all_materials_in_db = db.query(Material.name_en).all()
        # แปลงผลลัพธ์ [(name,), (name,)] ให้อยู่ในรูปแบบ [name, name]
        available_names = [name[0] for name in all_materials_in_db if name[0] is not None]
        print(f"🕵️‍♂️ AVAILABLE 'name_en' IN LOCAL DB: {available_names}")
    except Exception as e:
        print(f"❌ DEBUG ERROR: Could not fetch all material names from DB: {e}")
    # ========================================================

    # สร้างชุดคำค้นหาที่ครอบคลุมและสะอาด
    search_terms = set()
    for name in material_names:
        clean_name = name.strip().lower() 
        search_terms.add(clean_name)
        if clean_name.endswith('s'):
            search_terms.add(clean_name[:-1])
    
    print(f"🧐 Searching for terms: {list(search_terms)}")

    # สร้าง query ที่ค้นหาแบบไม่สนใจตัวพิมพ์และช่องว่าง
    query = db.query(Material).filter(func.lower(func.trim(Material.name_en)).in_(search_terms))
    found_materials = query.all()
    
    unique_materials = {mat.material_name: mat for mat in found_materials}.values()

    material_details = [
        {
            "material_name": mat.material_name,
            "unit_price_thb": float(mat.unit_price_thb),
            "unit_type": mat.unit_type
        }
        for mat in unique_materials
    ]
    print(f"🔍 Found materials in DB: {material_details}")
    return material_details

# --- ฟังก์ชัน calculate_quantities เหมือนเดิม ---
def calculate_quantities(materials: List[Dict], budget: float) -> List[Dict]:
    if not materials:
        return []

    sorted_materials = sorted(materials, key=lambda x: x['unit_price_thb'])
    
    bom_with_quantities = []
    remaining_budget = budget
    
    for mat in sorted_materials:
        if remaining_budget >= mat['unit_price_thb']:
            mat['quantity'] = 1
            remaining_budget -= mat['unit_price_thb']
        else:
            mat['quantity'] = 0
    
    while remaining_budget > 0:
        added_something = False
        for mat in sorted_materials:
            if mat['quantity'] > 0 and remaining_budget >= mat['unit_price_thb']:
                mat['quantity'] += 1
                remaining_budget -= mat['unit_price_thb']
                added_something = True
        if not added_something:
            break
            
    for mat in sorted_materials:
        mat['estimated_cost'] = mat['quantity'] * mat['unit_price_thb']

    final_bom = [mat for mat in sorted_materials if mat['quantity'] > 0]
    print(f"✅ Calculated quantities: {final_bom}")
    return final_bom


# --- ฟังก์ชันหลัก analyze_bom_from_image เหมือนเดิม ---
def analyze_bom_from_image(history_id: int, image_url: str, db: Session, budget: Optional[float] = 100000.0) -> List[BOMItem]:
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image_b64 = base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to load image from {image_url}: {str(e)}")

    material_names = get_materials_from_image(image_b64)
    if not material_names:
        print("⚠️ AI could not identify any materials. Using fallback.")
        return default_bom_fallback(budget)

    material_details = get_material_details_from_db(material_names, db)
    if not material_details:
        print("⚠️ No matching materials found in DB. Using fallback.")
        return default_bom_fallback(budget)

    final_bom_data = calculate_quantities(material_details, budget)

    return [
        BOMItem(
            material_name=item["material_name"],
            quantity=item["quantity"],
            unit_type=item["unit_type"],
            estimated_cost=item["estimated_cost"],
            affiliate_link=""
        )
        for item in final_bom_data
    ]

# --- ฟังก์ชัน default_bom_fallback เหมือนเดิม ---
def default_bom_fallback(budget: Optional[float] = None) -> List[BOMItem]:
    cost = 150.00
    if budget:
        cost = min(cost, budget / 10)
    return [
        BOMItem(
            material_name="ดินปลูก", 
            quantity=10, 
            unit_type="ถุง",
            estimated_cost=cost * 10, 
            affiliate_link="https://shopee.co.th/dirt"
        )
    ]
