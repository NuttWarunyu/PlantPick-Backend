from typing import List, Optional, Dict
from pydantic import BaseModel
import os
from openai import OpenAI
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
# === จุดแก้ไขที่ 1: Import โมเดลใหม่ทั้งหมด ===
from app.database import Material, Vendor, Product
import requests
from PIL import Image
import io
import base64
import json
import re

# ตั้งค่า OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === จุดแก้ไขที่ 2: อัปเดต Pydantic Model ให้รองรับข้อมูลร้านค้า ===
class BOMItem(BaseModel):
    material_name: str
    quantity: int
    unit_type: str
    vendor_name: str # เพิ่มชื่อร้านค้า
    unit_price: float # เพิ่มราคาต่อหน่วย
    estimated_cost: float
    product_url: Optional[str] = None

# --- ฟังก์ชันนี้เหมือนเดิม ---
def get_materials_from_image(image_b64: str) -> List[str]:
    """ใช้ AI Vision เพื่อลิสต์ชื่อวัสดุที่เห็นในภาพ"""
    try:
        # ... (โค้ดส่วนนี้เหมือนเดิม) ...
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

# --- ฟังก์ชันใหม่: ค้นหาสินค้าที่ราคาถูกที่สุดสำหรับแต่ละวัสดุ ---
def find_cheapest_products_in_db(material_names: List[str], db: Session) -> List[Dict]:
    """
    สำหรับวัสดุแต่ละชนิดที่ AI หาเจอ, ค้นหาว่าร้านไหนขายถูกที่สุด
    """
    if not material_names:
        return []

    search_terms = set()
    for name in material_names:
        clean_name = name.strip().lower()
        search_terms.add(clean_name)
        if clean_name.endswith('s'):
            search_terms.add(clean_name[:-1])

    # Query ที่ซับซ้อนขึ้นเพื่อหาราคาที่ถูกที่สุดของแต่ละ material
    # เราจะใช้ Subquery เพื่อหา min_price ของแต่ละ material_id ก่อน
    subquery = (
        db.query(Product.material_id, func.min(Product.price_thb).label("min_price"))
        .group_by(Product.material_id)
        .subquery()
    )

    # จากนั้น JOIN เพื่อหาข้อมูลทั้งหมดของสินค้าที่ราคาตรงกับ min_price
    query = (
        db.query(Product, Vendor, Material)
        .join(subquery, (Product.material_id == subquery.c.material_id) & (Product.price_thb == subquery.c.min_price))
        .join(Vendor, Product.vendor_id == Vendor.id)
        .join(Material, Product.material_id == Material.id)
        .filter(func.lower(func.trim(Material.name_en)).in_(search_terms))
    )
    
    results = query.all()
    
    cheapest_products = [
        {
            "material_name": material.material_name,
            "unit_price_thb": float(product.price_thb),
            "unit_type": product.unit_type,
            "vendor_name": vendor.vendor_name,
            "product_url": product.product_url
        }
        for product, vendor, material in results
    ]
    
    print(f"🛍️ Found cheapest products in DB: {cheapest_products}")
    return cheapest_products

# --- ฟังก์ชันคำนวณจำนวน (ปรับปรุงเล็กน้อย) ---
def calculate_quantities(products: List[Dict], budget: float) -> List[Dict]:
    """คำนวณจำนวนที่เหมาะสมสำหรับแต่ละสินค้าภายใต้งบประมาณ"""
    if not products:
        return []

    # เรียงจากถูกไปแพง
    sorted_products = sorted(products, key=lambda x: x['unit_price_thb'])
    
    remaining_budget = budget
    
    # ให้ทุกอย่างมีอย่างน้อย 1 ชิ้นก่อน
    for prod in sorted_products:
        if remaining_budget >= prod['unit_price_thb']:
            prod['quantity'] = 1
            remaining_budget -= prod['unit_price_thb']
        else:
            prod['quantity'] = 0
    
    # วนลูปเพิ่มจำนวนของชิ้นที่ถูกที่สุด
    while remaining_budget > 0:
        added_something = False
        for prod in sorted_products:
            if prod['quantity'] > 0 and remaining_budget >= prod['unit_price_thb']:
                prod['quantity'] += 1
                remaining_budget -= prod['unit_price_thb']
                added_something = True
        if not added_something:
            break
            
    # คำนวณราคารวมของแต่ละรายการ
    for prod in sorted_products:
        prod['estimated_cost'] = prod['quantity'] * prod['unit_price_thb']

    final_bom = [prod for prod in sorted_products if prod['quantity'] > 0]
    print(f"✅ Calculated quantities with vendors: {final_bom}")
    return final_bom


# --- ฟังก์ชันหลักที่ถูกเรียกจาก API (เขียนใหม่เกือบทั้งหมด) ---
def analyze_bom_from_image(history_id: int, image_url: str, db: Session, budget: Optional[float] = 100000.0) -> List[BOMItem]:
    """
    Workflow ใหม่สำหรับ Marketplace:
    1. โหลดรูป
    2. AI วิเคราะห์วัสดุ
    3. ค้นหาสินค้าที่ถูกที่สุดจากทุกร้าน
    4. คำนวณจำนวนตามงบ
    5. ประกอบร่างเป็น BOM สุดท้าย
    """
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image_b64 = base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to load image from {image_url}: {str(e)}")

    material_names = get_materials_from_image(image_b64)
    if not material_names:
        return default_bom_fallback(budget)

    cheapest_products = find_cheapest_products_in_db(material_names, db)
    if not cheapest_products:
        return default_bom_fallback(budget)

    final_bom_data = calculate_quantities(cheapest_products, budget)

    return [
        BOMItem(
            material_name=item["material_name"],
            quantity=item["quantity"],
            unit_type=item["unit_type"],
            vendor_name=item["vendor_name"],
            unit_price=item["unit_price_thb"],
            estimated_cost=item["estimated_cost"],
            product_url=item.get("product_url")
        )
        for item in final_bom_data
    ]

# --- ฟังก์ชันสำรอง (อัปเดตให้ตรงกับ Model ใหม่) ---
def default_bom_fallback(budget: Optional[float] = None) -> List[BOMItem]:
    cost = 150.00
    if budget:
        cost = min(cost, budget / 10)
    return [
        BOMItem(
            material_name="ดินปลูก", 
            quantity=10, 
            unit_type="ถุง",
            vendor_name="ร้านค้าแนะนำ",
            unit_price=cost,
            estimated_cost=cost * 10, 
            product_url="https://shopee.co.th/dirt"
        )
    ]
