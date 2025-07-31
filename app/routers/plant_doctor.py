from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import aiofiles
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
import json

router = APIRouter(prefix="/plant", tags=["Plant Doctor"])

# Mock database for plant diseases
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
        
        # Mock AI analysis (ในอนาคตจะใช้ AI จริง)
        # Simulate processing time
        import asyncio
        await asyncio.sleep(2)
        
        # Mock analysis result
        import random
        detected_diseases = random.sample(list(PLANT_DISEASES.keys()), random.randint(1, 2))
        
        analysis_result = {
            "plant_name": "ต้นไม้ทั่วไป",
            "light": "ปานกลาง",
            "water": "ปานกลาง",
            "diseases": [],
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