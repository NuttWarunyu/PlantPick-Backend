from typing import List, Optional, Dict
from pydantic import BaseModel
import os
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func
# === Import โมเดลใหม่ทั้งหมด ===
from app.database import Material, Vendor, Product, AITermMapping
import requests
from PIL import Image
import io
import base64
import json
import re
import random # <-- Import ไลบรารีสำหรับสุ่ม

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class BOMItem(BaseModel):
    material_name: str
    quantity: int
    unit_type: str
    vendor_name: str
    unit_price: float
    estimated_cost: float
    product_url: Optional[str] = None

def get_materials_from_image(image_b64: str) -> List[str]:
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": [{"type": "text", "text": "Analyze this garden image and list all visible materials like plants, stones, wood, etc. Return only a clean JSON array of strings. For example: [\"Palm Tree\", \"Paving Stone\", \"Wooden Deck\"]. Do not include any explanation."}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}]}], max_tokens=200)
        raw_response = response.choices[0].message.content
        cleaned_response = re.sub(r"```(?:json)?|```", "", raw_response).strip()
        material_list = json.loads(cleaned_response)
        print(f"🧠 AI identified materials: {material_list}")
        return [str(item) for item in material_list]
    except Exception as e:
        print(f"❌ Error getting materials from image: {e}")
        return []

# --- ฟังก์ชันหลักที่ถูกเรียกจาก API (เขียนใหม่ทั้งหมด) ---
def analyze_bom_from_image(history_id: int, image_url: str, db: Session, budget: Optional[float] = 100000.0) -> Dict:
    """
    Workflow ใหม่สำหรับ Smart Substitution ที่ให้ผลลัพธ์หลากหลายและมีคำแนะนำ
    """
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image_b64 = base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to load image from {image_url}: {str(e)}")

    # === จุดแก้ไขที่ 1: กำหนด "สูตรสำเร็จ" หรือสัดส่วนของสวนที่ต้องการ ===
    garden_recipe = {
        'พรรณไม้': 8,
        'งานฮาร์ดสเคป': 4,
        'ของตกแต่ง': 2,
        'ระบบ': 1
    }
    
    main_bom_candidates = []
    suggestions = {}
    added_material_ids = set()

    # วนลูปตาม "สูตร" ที่เรากำหนด
    for category, count in garden_recipe.items():
        # ค้นหาสินค้าทั้งหมดในหมวดหมู่นั้นๆ ที่ยังไม่ถูกเลือก
        query = (
            db.query(Product, Vendor, Material)
            .join(Vendor, Product.vendor_id == Vendor.id)
            .join(Material, Product.material_id == Material.id)
            .filter(Material.category == category)
            .filter(Material.id.notin_(added_material_ids))
            .order_by(func.random())
        )
        
        available_products = query.all()
        
        if not available_products:
            continue

        # สุ่มเลือกสินค้าตามจำนวนที่ต้องการในสูตร
        num_to_select = min(count, len(available_products))
        selected_products_tuples = random.sample(available_products, num_to_select)
        
        # เพิ่มสินค้าที่สุ่มเลือกได้ลงใน BOM หลัก
        for product, vendor, material in selected_products_tuples:
            main_bom_candidates.append({
                "material_id": material.id,
                "material_name": material.material_name,
                "category": material.category,
                "unit_price_thb": float(product.price_thb),
                "unit_type": product.unit_type,
                "vendor_name": vendor.vendor_name,
                "product_url": product.product_url
            })
            added_material_ids.add(material.id)

        # === จุดแก้ไขที่ 2: นำสินค้าที่เหลือในหมวดหมู่นี้ไปเป็น "คำแนะนำเพิ่มเติม" ===
        remaining_products = [p for p in available_products if p[2].id not in added_material_ids]
        if remaining_products:
            suggestion_key = f"ตัวเลือกเพิ่มเติมสำหรับ '{category}'"
            suggestions[suggestion_key] = [
                {
                    "material_name": material.material_name,
                    "unit_price_thb": float(product.price_thb),
                    "unit_type": product.unit_type,
                    "vendor_name": vendor.vendor_name,
                    "product_url": product.product_url
                }
                for product, vendor, material in remaining_products[:3] # แสดงคำแนะนำสูงสุด 3 รายการ
            ]


    print(f"🛍️ Final candidate products based on recipe: {main_bom_candidates}")
    if not main_bom_candidates:
        return {"main_bom": default_bom_fallback(budget), "suggestions": {}}

    # คำนวณจำนวนและประกอบร่าง BOM หลัก
    final_bom_data = calculate_quantities(main_bom_candidates, budget)
    main_bom_result = [BOMItem(**item) for item in final_bom_data]
    
    return {"main_bom": main_bom_result, "suggestions": suggestions}


def calculate_quantities(products: List[Dict], budget: float) -> List[Dict]:
    """คำนวณจำนวนที่เหมาะสมสำหรับแต่ละสินค้าภายใต้งบประมาณ พร้อมจำกัดจำนวนไม้ยืนต้น"""
    if not products: return []
    
    # เรียงจากถูกไปแพงเพื่อให้การกระจายงบประมาณมีประสิทธิภาพ
    sorted_products = sorted(products, key=lambda x: x['unit_price_thb'])
    remaining_budget = budget
    
    # ให้ทุกอย่างมีอย่างน้อย 1 ชิ้นก่อน
    for prod in sorted_products:
        if remaining_budget >= prod['unit_price_thb']:
            prod['quantity'] = 1
            remaining_budget -= prod['unit_price_thb']
        else:
            prod['quantity'] = 0
    
    # วนลูปเพิ่มจำนวน
    while remaining_budget > 0:
        added_something = False
        for prod in sorted_products:
            # กำหนดเงื่อนไขสำหรับ "ไม้ยืนต้น" (เช่น ราคาสูงกว่า 800 บาท)
            is_tree = (prod.get('category') == 'พรรณไม้' and 
                       prod.get('unit_type') == 'ต้น' and 
                       prod.get('unit_price_thb', 0) > 800)

            if prod['quantity'] > 0 and remaining_budget >= prod['unit_price_thb']:
                # ถ้าเป็นไม้ยืนต้นและมีจำนวนใกล้จะเต็มแล้ว (10 ต้น) ให้ข้ามไป
                if is_tree and prod['quantity'] >= 10:
                    continue
                
                prod['quantity'] += 1
                remaining_budget -= prod['unit_price_thb']
                added_something = True
        
        if not added_something: break
            
    for prod in sorted_products:
        prod['estimated_cost'] = prod['quantity'] * prod['unit_price_thb']
        prod['unit_price'] = prod['unit_price_thb']
        
    final_bom = [prod for prod in sorted_products if prod['quantity'] > 0]
    print(f"✅ Calculated quantities with vendors: {final_bom}")
    return final_bom

def default_bom_fallback(budget: Optional[float] = None) -> List[BOMItem]:
    cost = 150.00
    if budget: cost = min(cost, budget / 10)
    return [BOMItem(material_name="ดินปลูก", quantity=10, unit_type="ถุง", vendor_name="ร้านค้าแนะนำ", unit_price=cost, estimated_cost=cost * 10, product_url="https://shopee.co.th/dirt")]
