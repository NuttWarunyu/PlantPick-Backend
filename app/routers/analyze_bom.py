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
    material_name: str; quantity: int; unit_type: str; vendor_name: str; unit_price: float; estimated_cost: float; product_url: Optional[str] = None

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

def find_best_products_by_category(category: str, db: Session, limit: int = 5) -> List[Dict]:
    """สำหรับ Category ที่กำหนด, ค้นหาสินค้ามาตามจำนวนที่ระบุ"""
    query = (
        db.query(Product, Vendor, Material)
        .join(Vendor, Product.vendor_id == Vendor.id)
        .join(Material, Product.material_id == Material.id)
        .filter(Material.category == category)
        .order_by(func.random()) # <-- สุ่มลำดับเพื่อให้ได้ผลลัพธ์ที่หลากหลาย
        .limit(limit)
    )
    best_products = query.all()
    if not best_products:
        return []
    return [
        {
            "material_id": material.id, # ส่ง ID ไปด้วยเพื่อใช้เช็คของซ้ำ
            "material_name": material.material_name,
            "category": material.category, # ส่ง Category ไปด้วยเพื่อใช้จำกัดจำนวน
            "unit_price_thb": float(product.price_thb),
            "unit_type": product.unit_type,
            "vendor_name": vendor.vendor_name,
            "product_url": product.product_url
        }
        for product, vendor, material in best_products
    ]

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

    ai_material_names = get_materials_from_image(image_b64)
    if not ai_material_names:
        return {"main_bom": default_bom_fallback(budget), "suggestions": {}}

    main_bom_candidates = []
    suggestions = {}
    added_material_ids = set()

    for name in ai_material_names:
        clean_name = name.strip().lower()
        singular_name = clean_name[:-1] if clean_name.endswith('s') else clean_name

        # 1. พยายามหาแบบเจาะจงก่อน (Direct Match)
        direct_match_query = (
            db.query(Product, Vendor, Material)
            .join(Vendor, Product.vendor_id == Vendor.id)
            .join(Material, Product.material_id == Material.id)
            .filter(func.lower(Material.name_en).in_([clean_name, singular_name]))
            .filter(Material.id.notin_(added_material_ids))
            .order_by(Product.price_thb.asc())
        )
        found_product = direct_match_query.first()
        
        if found_product:
            product, vendor, material = found_product
            main_bom_candidates.append({
                "material_id": material.id, "material_name": material.material_name, "category": material.category,
                "unit_price_thb": float(product.price_thb), "unit_type": product.unit_type,
                "vendor_name": vendor.vendor_name, "product_url": product.product_url
            })
            added_material_ids.add(material.id)
            continue

        # 2. ถ้าหาไม่เจอ ให้ไปหาใน "พจนานุกรม" (Mapping Table)
        mapping_query = db.query(AITermMapping).filter(func.lower(AITermMapping.ai_term) == clean_name)
        mapping = mapping_query.first()

        if mapping:
            print(f"↪️ Mapping '{name}' to category '{mapping.maps_to_category}'")
            best_products_in_category = find_best_products_by_category(mapping.maps_to_category, db, limit=3)
            
            if best_products_in_category:
                # เพิ่มตัวเลือกที่ดีที่สุด (ตัวแรก) ลงใน BOM หลัก
                main_choice = best_products_in_category[0]
                if main_choice["material_id"] not in added_material_ids:
                    main_bom_candidates.append(main_choice)
                    added_material_ids.add(main_choice["material_id"])
                
                # เก็บตัวเลือกที่เหลือเป็นคำแนะนำ
                if len(best_products_in_category) > 1:
                    suggestion_key = f"สำหรับหมวดหมู่ '{mapping.maps_to_category}'"
                    if suggestion_key not in suggestions:
                        suggestions[suggestion_key] = []
                    
                    for item in best_products_in_category[1:]:
                        if item["material_id"] not in added_material_ids:
                             suggestions[suggestion_key].append(item)

    print(f"🛍️ Final candidate products for BOM: {main_bom_candidates}")
    if not main_bom_candidates:
        return {"main_bom": default_bom_fallback(budget), "suggestions": {}}

    final_bom_data = calculate_quantities(main_bom_candidates, budget)
    main_bom_result = [BOMItem(**item) for item in final_bom_data]
    
    return {"main_bom": main_bom_result, "suggestions": suggestions}


def calculate_quantities(products: List[Dict], budget: float) -> List[Dict]:
    """คำนวณจำนวนที่เหมาะสมสำหรับแต่ละสินค้าภายใต้งบประมาณ พร้อมจำกัดจำนวนไม้ยืนต้น"""
    if not products: return []
    
    sorted_products = sorted(products, key=lambda x: x['unit_price_thb'])
    remaining_budget = budget
    
    for prod in sorted_products:
        if remaining_budget >= prod['unit_price_thb']:
            prod['quantity'] = 1
            remaining_budget -= prod['unit_price_thb']
        else:
            prod['quantity'] = 0
    
    while remaining_budget > 0:
        added_something = False
        for prod in sorted_products:
            # === จุดแก้ไขหลัก: จำกัดจำนวนไม้ยืนต้นไม่ให้เกิน 10 ต้น ===
            # เราจะสมมติว่า ไม้ยืนต้นคือสินค้าในหมวด 'พรรณไม้' ที่มีหน่วยเป็น 'ต้น' และราคาสูง
            is_tree = (prod.get('category') == 'พรรณไม้' and 
                       prod.get('unit_type') == 'ต้น' and 
                       prod.get('unit_price_thb', 0) > 500) # กรองเอาเฉพาะต้นไม้ใหญ่

            if prod['quantity'] > 0 and remaining_budget >= prod['unit_price_thb']:
                # ถ้าเป็นไม้ยืนต้นและมีจำนวนใกล้จะเต็มแล้ว ให้ข้ามไป
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
