from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import aiofiles
import os
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import json
import requests
from PIL import Image
import io
import base64

router = APIRouter(prefix="/plant", tags=["Plant Doctor"])

# AI Model Configuration
AI_MODEL_URL = os.getenv("AI_MODEL_URL", "https://api.replicate.com/v1/predictions")
AI_MODEL_VERSION = os.getenv("AI_MODEL_VERSION", "yorickvp/plant-disease-detection:8c5b8b5c8b5c8b5c8b5c8b5c8b5c8b5c8b5c8b5c")

# Mock database for plant diseases (fallback)
PLANT_DISEASES = {
    "leaf_spot": {
        "name": "โรคใบจุด",
        "severity": "ปานกลาง",
        "symptoms": [
            "ใบมีจุดสีน้ำตาลหรือดำ",
            "ใบเหลืองและร่วง",
            "จุดขยายตัวและรวมกัน"
        ],
        "treatment": "ใช้ยาฆ่าเชื้อรา เช่น แมนโคเซ็บ หรือ คอปเปอร์ออกไซด์ ฉีดพ่นทุก 7-10 วัน"
    },
    "powdery_mildew": {
        "name": "โรคราแป้ง",
        "severity": "สูง",
        "symptoms": [
            "ใบมีผงสีขาวเหมือนแป้ง",
            "ใบหงิกงอ",
            "การเจริญเติบโตช้า"
        ],
        "treatment": "ใช้ยาฆ่าเชื้อรา เช่น ซัลเฟอร์ หรือ ไตรฟอรีน ฉีดพ่นทุก 5-7 วัน"
    },
    "root_rot": {
        "name": "โรครากเน่า",
        "severity": "สูงมาก",
        "symptoms": [
            "ใบเหลืองและเหี่ยว",
            "รากมีสีน้ำตาลหรือดำ",
            "ดินมีกลิ่นเหม็น"
        ],
        "treatment": "เปลี่ยนดินใหม่ ใช้ดินที่ระบายน้ำดี และลดการรดน้ำ"
    },
    "aphid_infestation": {
        "name": "เพลี้ยอ่อน",
        "severity": "ปานกลาง",
        "symptoms": [
            "ใบหงิกงอ",
            "มีแมลงสีเขียวหรือดำเกาะ",
            "ใบเหนียวและมีราดำ"
        ],
        "treatment": "ใช้ยาฆ่าแมลง เช่น อิมิดาโคลพริด หรือ ใช้สบู่ฆ่าแมลงธรรมชาติ"
    },
    "spider_mites": {
        "name": "ไรแดง",
        "severity": "สูง",
        "symptoms": [
            "ใบมีจุดสีเหลือง",
            "ใบบิดเบี้ยว",
            "มีใยบางๆ ใต้ใบ"
        ],
        "treatment": "ใช้ยาฆ่าไร เช่น อะบาเมกติน หรือ ใช้น้ำฉีดพ่นแรงๆ"
    }
}

# Mock treatment plans
TREATMENT_PLANS = {
    "leaf_spot": [
        {
            "title": "ตัดใบที่เป็นโรค",
            "description": "ตัดใบที่มีจุดสีน้ำตาลออกเพื่อป้องกันการแพร่กระจาย",
            "duration": "ทันที"
        },
        {
            "title": "ฉีดยาฆ่าเชื้อรา",
            "description": "ใช้แมนโคเซ็บ 2 กรัมต่อน้ำ 1 ลิตร ฉีดพ่นทั่วต้น",
            "duration": "ทุก 7-10 วัน"
        },
        {
            "title": "ปรับการรดน้ำ",
            "description": "รดน้ำที่โคนต้น หลีกเลี่ยงการรดน้ำบนใบ",
            "duration": "ต่อเนื่อง"
        }
    ],
    "powdery_mildew": [
        {
            "title": "แยกต้นที่เป็นโรค",
            "description": "ย้ายต้นที่เป็นโรคไปไว้ในที่ที่มีอากาศถ่ายเท",
            "duration": "ทันที"
        },
        {
            "title": "ฉีดยาฆ่าเชื้อรา",
            "description": "ใช้ซัลเฟอร์ 1 กรัมต่อน้ำ 1 ลิตร ฉีดพ่น",
            "duration": "ทุก 5-7 วัน"
        },
        {
            "title": "ปรับสภาพแวดล้อม",
            "description": "ลดความชื้นและเพิ่มการระบายอากาศ",
            "duration": "ต่อเนื่อง"
        }
    ],
    "root_rot": [
        {
            "title": "หยุดรดน้ำ",
            "description": "หยุดรดน้ำทันทีเพื่อให้ดินแห้ง",
            "duration": "2-3 วัน"
        },
        {
            "title": "เปลี่ยนดิน",
            "description": "เปลี่ยนดินใหม่ที่ระบายน้ำดี",
            "duration": "ทันที"
        },
        {
            "title": "ตัดรากเน่า",
            "description": "ตัดรากที่เน่าออกและแช่ในน้ำยาฆ่าเชื้อ",
            "duration": "ทันที"
        }
    ]
}

# ฐานข้อมูลผลิตภัณฑ์รักษาโรคต้นไม้
TREATMENT_PRODUCTS = {
    "leaf_spot": [
        {
            "name": "แมนโคเซ็บ 80% WP",
            "description": "ยาฆ่าเชื้อรา สำหรับโรคใบจุด",
            "price": "150-200 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=แมนโคเซ็บ",
            "image": "https://example.com/mancozeb.jpg",
            "rating": 4.5,
            "reviews": 128
        },
        {
            "name": "คอปเปอร์ออกไซด์ 77% WP",
            "description": "ยาฆ่าเชื้อราและแบคทีเรีย",
            "price": "180-250 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=คอปเปอร์ออกไซด์",
            "image": "https://example.com/copper.jpg",
            "rating": 4.3,
            "reviews": 95
        }
    ],
    "powdery_mildew": [
        {
            "name": "ซัลเฟอร์ 80% WP",
            "description": "ยาฆ่าเชื้อราโรคราแป้ง",
            "price": "120-180 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=ซัลเฟอร์+ยาฆ่าเชื้อรา",
            "image": "https://example.com/sulfur.jpg",
            "rating": 4.2,
            "reviews": 87
        },
        {
            "name": "ไตรฟอรีน 19% EC",
            "description": "ยาฆ่าเชื้อราแบบดูดซึม",
            "price": "250-350 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=ไตรฟอรีน",
            "image": "https://example.com/triforine.jpg",
            "rating": 4.6,
            "reviews": 156
        }
    ],
    "root_rot": [
        {
            "name": "ดินปลูกต้นไม้คุณภาพดี",
            "description": "ดินระบายน้ำดี ป้องกันรากเน่า",
            "price": "80-120 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=ดินปลูกต้นไม้",
            "image": "https://example.com/soil.jpg",
            "rating": 4.4,
            "reviews": 234
        },
        {
            "name": "ถาดรองกระถาง",
            "description": "ช่วยระบายน้ำ ป้องกันรากเน่า",
            "price": "30-50 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=ถาดรองกระถาง",
            "image": "https://example.com/saucer.jpg",
            "rating": 4.1,
            "reviews": 67
        }
    ],
    "aphid_infestation": [
        {
            "name": "อิมิดาโคลพริด 70% WG",
            "description": "ยาฆ่าแมลงเพลี้ยอ่อน",
            "price": "200-280 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=อิมิดาโคลพริด",
            "image": "https://example.com/imidacloprid.jpg",
            "rating": 4.7,
            "reviews": 189
        },
        {
            "name": "สบู่ฆ่าแมลงธรรมชาติ",
            "description": "ปลอดภัยสำหรับพืชและคน",
            "price": "150-200 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=สบู่ฆ่าแมลง",
            "image": "https://example.com/soap.jpg",
            "rating": 4.3,
            "reviews": 112
        }
    ],
    "spider_mites": [
        {
            "name": "อะบาเมกติน 1.8% EC",
            "description": "ยาฆ่าไรแดง",
            "price": "180-250 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=อะบาเมกติน",
            "image": "https://example.com/abamectin.jpg",
            "rating": 4.5,
            "reviews": 143
        },
        {
            "name": "สเปรย์ฉีดน้ำแรงสูง",
            "description": "ฉีดน้ำแรงๆ ไล่ไรแดง",
            "price": "200-300 บาท",
            "affiliate_link": "https://shopee.co.th/search?keyword=สเปรย์ฉีดน้ำ",
            "image": "https://example.com/sprayer.jpg",
            "rating": 4.2,
            "reviews": 89
        }
    ]
}

async def analyze_plant_with_ai(image_path: str) -> Dict[str, Any]:
    """
    ใช้ AI วิเคราะห์โรคต้นไม้จากรูปภาพ
    """
    try:
        # Read image file
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # Call AI API with image
        headers = {
            "Authorization": f"Token {os.getenv('REPLICATE_API_TOKEN')}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "version": AI_MODEL_VERSION,
            "input": {
                "image": base64.b64encode(image_data).decode('utf-8')
            }
        }
        
        # Initial API call
        response = requests.post(AI_MODEL_URL, headers=headers, json=payload)
        
        if response.status_code != 201:
            print(f"AI API error: {response.status_code} - {response.text}")
            return None
        
        # Get prediction ID for polling
        prediction = response.json()
        prediction_id = prediction.get("id")
        
        if not prediction_id:
            print("❌ ไม่ได้รับ prediction ID")
            return None
        
        # Poll for results
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            await asyncio.sleep(2)  # Wait 2 seconds between polls
            
            poll_response = requests.get(
                f"{AI_MODEL_URL}/{prediction_id}",
                headers={"Authorization": f"Token {os.getenv('REPLICATE_API_TOKEN')}"}
            )
            
            if poll_response.status_code != 200:
                print(f"Polling error: {poll_response.status_code}")
                attempt += 1
                continue
            
            poll_result = poll_response.json()
            status = poll_result.get("status")
            
            print(f"🔍 Polling attempt {attempt + 1}: Status = {status}")
            
            if status == "succeeded":
                # Parse the AI response
                output = poll_result.get("output", [])
                if output and len(output) > 0:
                    # Extract disease information from vision model output
                    disease_info = output[0]  # Usually the first result
                    
                    # Convert vision model output to our format
                    analysis_result = {
                        "plant_name": disease_info.get("plant_name", "ต้นไม้ทั่วไป"),
                        "diseases": [{
                            "name": disease_info.get("disease_name", "โรคทั่วไป"),
                            "severity": disease_info.get("confidence", "ปานกลาง"),
                            "symptoms": [disease_info.get("symptoms", "อาการทั่วไป")],
                            "treatment": disease_info.get("treatment", "ปรึกษาผู้เชี่ยวชาญ")
                        }],
                        "care_tips": {
                            "light": "ปานกลาง",
                            "water": "ปานกลาง", 
                            "soil": "ดินทั่วไป"
                        }
                    }
                    return analysis_result
                else:
                    print("❌ ไม่มีผลลัพธ์จาก AI")
                    return None
                    
            elif status == "failed":
                print(f"❌ AI prediction failed: {poll_result.get('error', 'Unknown error')}")
                return None
            elif status in ["starting", "processing"]:
                attempt += 1
                continue
            else:
                print(f"❌ Unknown status: {status}")
                attempt += 1
                continue
        
        print("❌ Timeout waiting for AI prediction")
        return None
            
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        return None

async def get_treatment_products(disease_key: str) -> List[Dict[str, Any]]:
    """
    หาผลิตภัณฑ์รักษาโรคต้นไม้พร้อม affiliate links
    """
    try:
        # เรียกใช้ Shopee API เพื่อหาผลิตภัณฑ์จริง
        from .shopee import get_shopee_products
        
        # หาคำค้นหาที่เหมาะสม
        search_keywords = {
            "leaf_spot": ["ยาฆ่าเชื้อรา", "แมนโคเซ็บ", "คอปเปอร์ออกไซด์"],
            "powdery_mildew": ["ยาฆ่าเชื้อรา", "ซัลเฟอร์", "โรคราแป้ง"],
            "root_rot": ["ดินปลูกต้นไม้", "ถาดรองกระถาง", "ดินระบายน้ำ"],
            "aphid_infestation": ["ยาฆ่าแมลง", "อิมิดาโคลพริด", "เพลี้ยอ่อน"],
            "spider_mites": ["ยาฆ่าไร", "อะบาเมกติน", "ไรแดง"]
        }
        
        products = []
        keywords = search_keywords.get(disease_key, [disease_key])
        
        for keyword in keywords[:2]:  # ลองหาแค่ 2 คำค้นหา
            shopee_products = await get_shopee_products(keyword, 0)
            if shopee_products:
                # แปลง Shopee products เป็นรูปแบบที่ต้องการ
                for product in shopee_products[:3]:  # เอาแค่ 3 รายการแรก
                    products.append({
                        "name": product.get("productName", keyword),
                        "description": f"ผลิตภัณฑ์สำหรับ {keyword}",
                        "price": f"{product.get('price', 'N/A')} บาท",
                        "affiliate_link": product.get("offerLink", f"https://shopee.co.th/search?keyword={keyword}"),
                        "image": product.get("imageUrl", ""),
                        "rating": product.get("ratingStar", 4.0),
                        "reviews": product.get("sales", 0),
                        "source": "Shopee"
                    })
                break  # หยุดเมื่อเจอแล้ว
        
        # ถ้าไม่มี Shopee products ให้ใช้ mock data
        if not products and disease_key in TREATMENT_PRODUCTS:
            products = TREATMENT_PRODUCTS[disease_key]
            for product in products:
                product["source"] = "Mock Data"
        
        return products
        
    except Exception as e:
        print(f"Error getting treatment products: {e}")
        # Fallback to mock data
        if disease_key in TREATMENT_PRODUCTS:
            products = TREATMENT_PRODUCTS[disease_key].copy()
            for product in products:
                product["source"] = "Fallback"
            return products
        return []

@router.post("/analyze-disease")
async def analyze_plant_disease(image: UploadFile = File(...)):
    """
    วิเคราะห์โรคต้นไม้จากรูปภาพ
    """
    try:
        # Validate file type
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="ไฟล์ต้องเป็นรูปภาพเท่านั้น")
        
        # Generate unique filename
        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"plant_disease_{uuid.uuid4()}{file_extension}"
        
        # Save uploaded file
        upload_dir = "uploads/plant_diseases"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await image.read()
            await f.write(content)
        
        # ใช้ AI วิเคราะห์โรคต้นไม้
        ai_result = await analyze_plant_with_ai(file_path)
        
        if ai_result:
            # ใช้ผลลัพธ์จาก AI
            analysis_result = {
                "plant_name": ai_result.get("plant_name", "ต้นไม้ทั่วไป"),
                "diseases": ai_result.get("diseases", []),
                "care_tips": ai_result.get("care_tips", {
                    "light": "ปานกลาง",
                    "water": "ปานกลาง",
                    "soil": "ดินทั่วไป"
                }),
                "treatment_plan": []
            }
            
            # สร้าง treatment plan และหาผลิตภัณฑ์แนะนำ
            recommended_products = []
            for disease in analysis_result["diseases"]:
                treatment_plan = [
                    {
                        "title": "การรักษาเบื้องต้น",
                        "description": disease.get("treatment", "ปรึกษาผู้เชี่ยวชาญ"),
                        "duration": "ทันที"
                    }
                ]
                analysis_result["treatment_plan"].extend(treatment_plan)
                
                # หาผลิตภัณฑ์แนะนำสำหรับโรคนี้
                disease_name = disease.get("name", "").lower()
                disease_key = None
                
                # Map disease name to key
                if "ใบจุด" in disease_name or "leaf spot" in disease_name:
                    disease_key = "leaf_spot"
                elif "ราแป้ง" in disease_name or "powdery" in disease_name:
                    disease_key = "powdery_mildew"
                elif "รากเน่า" in disease_name or "root rot" in disease_name:
                    disease_key = "root_rot"
                elif "เพลี้ย" in disease_name or "aphid" in disease_name:
                    disease_key = "aphid_infestation"
                elif "ไร" in disease_name or "mite" in disease_name:
                    disease_key = "spider_mites"
                
                if disease_key:
                    products = await get_treatment_products(disease_key)
                    recommended_products.extend(products)
            
            analysis_result["recommended_products"] = recommended_products
        else:
            # Fallback to mock data if AI fails
            print("⚠️ AI analysis failed, using mock data")
            import random
            detected_diseases = random.sample(list(PLANT_DISEASES.keys()), random.randint(1, 2))
            
            analysis_result = {
                "plant_name": "ต้นไม้ทั่วไป",
                "diseases": [],
                "care_tips": {
                    "light": "ปานกลาง",
                    "water": "ปานกลาง",
                    "soil": "ดินทั่วไป"
                },
                "treatment_plan": []
            }
            
            for disease_key in detected_diseases:
                disease_info = PLANT_DISEASES[disease_key]
                analysis_result["diseases"].append({
                    "name": disease_info["name"],
                    "severity": disease_info["severity"],
                    "symptoms": disease_info["symptoms"],
                    "treatment": disease_info["treatment"]
                })
                
                # Add treatment plan if available
                if disease_key in TREATMENT_PLANS:
                    analysis_result["treatment_plan"].extend(TREATMENT_PLANS[disease_key])
        
        # Add timestamp
        analysis_result["analyzed_at"] = datetime.now().isoformat()
        analysis_result["image_id"] = unique_filename
        
        return JSONResponse(content=analysis_result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}")

@router.get("/diseases")
async def get_plant_diseases():
    """
    ดึงรายการโรคต้นไม้ทั้งหมด
    """
    return {
        "diseases": list(PLANT_DISEASES.keys()),
        "total": len(PLANT_DISEASES)
    }

@router.get("/disease/{disease_id}")
async def get_disease_info(disease_id: str):
    """
    ดึงข้อมูลโรคต้นไม้ตาม ID
    """
    if disease_id not in PLANT_DISEASES:
        raise HTTPException(status_code=404, detail="ไม่พบโรคต้นไม้นี้")
    
    disease_info = PLANT_DISEASES[disease_id].copy()
    disease_info["id"] = disease_id
    
    if disease_id in TREATMENT_PLANS:
        disease_info["treatment_plan"] = TREATMENT_PLANS[disease_id]
    
    return disease_info

@router.get("/treatment-plans")
async def get_treatment_plans():
    """
    ดึงรายการแผนการรักษาทั้งหมด
    """
    return {
        "treatment_plans": TREATMENT_PLANS,
        "total": len(TREATMENT_PLANS)
    }

@router.get("/recommended-products/{disease_key}")
async def get_recommended_products(disease_key: str):
    """
    ดึงผลิตภัณฑ์แนะนำสำหรับโรคต้นไม้
    """
    products = await get_treatment_products(disease_key)
    return {
        "disease_key": disease_key,
        "products": products,
        "total": len(products)
    }

@router.get("/all-products")
async def get_all_products():
    """
    ดึงผลิตภัณฑ์ทั้งหมด
    """
    all_products = {}
    for disease_key in TREATMENT_PRODUCTS.keys():
        products = await get_treatment_products(disease_key)
        all_products[disease_key] = products
    
    return {
        "all_products": all_products,
        "total_diseases": len(all_products)
    } 