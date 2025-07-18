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
        cleaned_response = re.sub(r"```(?:json)?|```", "", raw_response or "").strip()
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
    ปรับสัดส่วน BOM: ต้นไม้ 60%, วัสดุ 30%, ระบบ 10% (จำกัด BOM หลัก 10 รายการ)
    """
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image_b64 = base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to load image from {image_url}: {str(e)}")

    # --- กำหนดสัดส่วนงบประมาณ ---
    total_budget = float(budget or 100000.0)
    plant_budget = total_budget * 0.6
    material_budget = total_budget * 0.3
    system_budget = total_budget * 0.1

    # --- กำหนดกลุ่มย่อยและงบย่อย ---
    plant_groups = [
        {"name": "ต้นไม้ใหญ่", "category": "พรรณไม้", "unit_type": "ต้น", "min_price": 5000, "max_price": None, "budget": plant_budget * 0.4, "max_count": 3},
        {"name": "ต้นไม้กลาง", "category": "พรรณไม้", "unit_type": "ต้น", "min_price": 2000, "max_price": 5000, "budget": plant_budget * 0.44, "max_count": 6},
        {"name": "ไม้เล็ก/ดอกไม้", "category": "พรรณไม้", "unit_type": None, "min_price": None, "max_price": 2000, "budget": plant_budget * 0.16, "max_count": 15},
    ]
    material_groups = [
        {"name": "ทางเดิน/พื้นผิว", "category": "งานฮาร์ดสเคป", "budget": material_budget * 0.667, "max_count": 2},
        {"name": "ขอบแปลง/โซนนิ่ง", "category": "งานฮาร์ดสเคป", "budget": material_budget * 0.333, "max_count": 2},
    ]
    system_groups = [
        {"name": "ดิน/ปุ๋ย", "category": "ระบบ", "budget": system_budget * 0.533, "max_count": 1},
        {"name": "ระบบรดน้ำ", "category": "ระบบ", "budget": system_budget * 0.467, "max_count": 1},
    ]

    main_bom_candidates = []
    suggestions = {}
    added_material_ids = set()
    total_items = 0

    # --- เลือกสินค้าแต่ละกลุ่มย่อย ---
    def pick_products(group, filter_extra=None):
        nonlocal total_items
        query = (
            db.query(Product, Vendor, Material)
            .join(Vendor, Product.vendor_id == Vendor.id)
            .join(Material, Product.material_id == Material.id)
            .filter(Material.category == group["category"])
        )
        if group.get("unit_type"):
            query = query.filter(Product.unit_type == group["unit_type"])
        if group.get("min_price"):
            query = query.filter(Product.price_thb >= group["min_price"])
        if group.get("max_price"):
            query = query.filter(Product.price_thb < group["max_price"])
        if filter_extra:
            query = filter_extra(query)
        query = query.order_by(func.random())
        available_products = query.all()
        if not available_products:
            return []
        # เลือกสินค้าตามงบและจำนวนสูงสุด
        selected = []
        used_budget = 0
        for product, vendor, material in available_products:
            if total_items >= 10:
                break
            price = float(product.price_thb)
            if used_budget + price > group["budget"]:
                continue
            selected.append({
                "material_id": material.id,
                "material_name": material.material_name,
                "category": material.category,
                "unit_price_thb": price,
                "unit_type": product.unit_type,
                "vendor_name": vendor.vendor_name,
                "product_url": product.product_url
            })
            used_budget += price
            added_material_ids.add(material.id)
            total_items += 1
            if len(selected) >= group["max_count"]:
                break
        # --- เพิ่ม suggestions: สินค้าที่เหลือในกลุ่มนี้ (ที่ยังไม่ถูกเลือก) ---
        remaining = [
            (product, vendor, material)
            for product, vendor, material in available_products
            if material.id not in added_material_ids
        ]
        # แนะนำเฉพาะกลุ่ม 'ต้นไม้' (พรรณไม้) และ 'ของตกแต่ง' เท่านั้น
        if group["category"] in ["พรรณไม้", "ของตกแต่ง"] and remaining:
            suggestions[group["name"]] = [
                {
                    "material_name": material.material_name,
                    "unit_price_thb": float(product.price_thb),
                    "unit_type": product.unit_type,
                    "vendor_name": vendor.vendor_name,
                    "product_url": product.product_url
                }
                for product, vendor, material in remaining[:1]
            ]
        return selected

    # --- ต้นไม้ ---
    for group in plant_groups:
        main_bom_candidates.extend(pick_products(group))
    # --- วัสดุ ---
    for group in material_groups:
        main_bom_candidates.extend(pick_products(group))
    # --- ระบบ ---
    for group in system_groups:
        main_bom_candidates.extend(pick_products(group))

    # --- ถ้ายังไม่ครบ 10 รายการ ให้สุ่มเติมจากกลุ่มอื่น ---
    if len(main_bom_candidates) < 10:
        # ลองเติมจากพรรณไม้ก่อน
        extra = pick_products({"category": "พรรณไม้", "budget": total_budget, "max_count": 10-len(main_bom_candidates)})
        for item in extra:
            if len(main_bom_candidates) < 10:
                main_bom_candidates.append(item)

    print(f"🛍️ Final candidate products based on new recipe: {main_bom_candidates}")
    if not main_bom_candidates:
        return {"main_bom": default_bom_fallback(total_budget), "suggestions": {}}

    # คำนวณจำนวนและประกอบร่าง BOM หลัก
    final_bom_data = calculate_quantities(main_bom_candidates, total_budget)
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
