from typing import List, Optional, Dict
from pydantic import BaseModel
import os
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import Material, Vendor, Product, AITermMapping
import requests
from PIL import Image
import io
import base64
import json
import re

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

def find_best_products_by_category(category: str, db: Session, limit: int = 3) -> List[Dict]:
    query = (
        db.query(Product, Vendor, Material)
        .join(Vendor, Product.vendor_id == Vendor.id)
        .join(Material, Product.material_id == Material.id)
        .filter(Material.category == category)
        .order_by(Product.price_thb.asc())
        .limit(limit)
    )
    best_products = query.all()
    if not best_products:
        return []
    return [
        {
            "material_name": material.material_name,
            "unit_price_thb": float(product.price_thb),
            "unit_type": product.unit_type,
            "vendor_name": vendor.vendor_name,
            "product_url": product.product_url
        }
        for product, vendor, material in best_products
    ]

def analyze_bom_from_image(history_id: int, image_url: str, db: Session, budget: Optional[float] = 100000.0) -> Dict:
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
    processed_categories = set()
    processed_specific_materials = set()

    for name in ai_material_names:
        clean_name = name.strip().lower()
        
        direct_match_query = (
            db.query(Product, Vendor, Material)
            .join(Vendor, Product.vendor_id == Vendor.id)
            .join(Material, Product.material_id == Material.id)
            .filter(func.lower(Material.name_en) == clean_name)
            .order_by(Product.price_thb.asc())
        )
        found_product = direct_match_query.first()
        
        if found_product:
            product, vendor, material = found_product
            if material.material_name not in processed_specific_materials:
                main_bom_candidates.append({
                    "material_name": material.material_name, "unit_price_thb": float(product.price_thb),
                    "unit_type": product.unit_type, "vendor_name": vendor.vendor_name,
                    "product_url": product.product_url
                })
                processed_specific_materials.add(material.material_name)
            continue

        mapping_query = db.query(AITermMapping).filter(func.lower(AITermMapping.ai_term) == clean_name)
        mapping = mapping_query.first()

        if mapping and mapping.maps_to_category not in processed_categories:
            print(f"↪️ Mapping '{name}' to category '{mapping.maps_to_category}'")
            best_products_in_category = find_best_products_by_category(mapping.maps_to_category, db, limit=3)
            
            if best_products_in_category:
                main_bom_candidates.append(best_products_in_category[0])
                if len(best_products_in_category) > 1:
                    suggestion_key = f"สำหรับหมวดหมู่ '{mapping.maps_to_category}'"
                    suggestions[suggestion_key] = best_products_in_category[1:]
                processed_categories.add(mapping.maps_to_category)
    
    unique_candidates = list({v['material_name']:v for v in main_bom_candidates}.values())
    print(f"🛍️ Final candidate products for BOM: {unique_candidates}")
    
    if not unique_candidates:
        return {"main_bom": default_bom_fallback(budget), "suggestions": {}}

    final_bom_data = calculate_quantities(unique_candidates, budget)
    
    # === จุดแก้ไข: ส่ง suggestions เป็น dict ธรรมดา ไม่ต้องแปลงเป็น BOMItem ===
    main_bom_result = [BOMItem(**item) for item in final_bom_data]
    
    return {"main_bom": main_bom_result, "suggestions": suggestions}

def calculate_quantities(products: List[Dict], budget: float) -> List[Dict]:
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
            if prod['quantity'] > 0 and remaining_budget >= prod['unit_price_thb']:
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
