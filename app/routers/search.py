import os
import json
import re
from openai import AsyncOpenAI
from fastapi import HTTPException, APIRouter, Query

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
router = APIRouter()

@router.get("/search-by-name")
async def search_by_name(plant_name: str = Query(..., alias="name")):
    try:
        print(f"🔍 เริ่มค้นหาดีลต้นไม้: {plant_name}")

        # เรียก OpenAI เพื่อดึงข้อมูลต้นไม้
        prompt = """
        คุณเป็นผู้เชี่ยวชาญด้านพืช ช่วยให้ข้อมูลเกี่ยวกับต้นไม้ตามชื่อที่ให้มาในรูปแบบ JSON เท่านั้น (ห้ามใส่ข้อความอื่นนอกเหนือจาก JSON และต้องมีเครื่องหมาย {} เสมอ):

        {
          "name": "ชื่อต้นไม้ (ชื่อวิทยาศาสตร์) และลักษณะเด่น เช่น ดอกสีขาว",
          "price": "ราคาโดยประมาณในหน่วยบาท เช่น ~100 บาท",
          "description": "ลักษณะของต้นไม้ เช่น ไม้พุ่มขนาดเล็ก สูง 2-3 เมตร",
          "careInstructions": "วิธีการดูแล เช่น รดน้ำสัปดาห์ละ 2 ครั้ง ชอบแดดจัด",
          "gardenIdeas": "เหมาะกับสวนสไตล์ไหน เช่น เหมาะกับสวนสไตล์เมดิเตอร์เรเนียน"
        }

        ตัวอย่าง:
        {
          "name": "ลีลาวดีสีขาว (Plumbago auriculata) ดอกสีขาว",
          "price": "~100 บาท",
          "description": "ไม้พุ่มขนาดเล็กถึงขนาดกลาง สูง 2-3 เมตร ดอกสีขาว",
          "careInstructions": "รดน้ำสัปดาห์ละ 2 ครั้ง ชอบแดดจัด",
          "gardenIdeas": "เหมาะกับสวนสไตล์เมดิเตอร์เรเนียน หรือจัดเป็นไม้พุ่มแนวรั้ว"
        }

        ถ้าไม่รู้จักต้นไม้ ให้ตอบกลับ:
        {
          "name": "ไม่รู้จักต้นไม้",
          "price": "ไม่มีข้อมูล",
          "description": "ไม่มีข้อมูล",
          "careInstructions": "ไม่มีข้อมูล",
          "gardenIdeas": "ไม่มีข้อมูล"
        }

        ห้ามตอบเป็นข้อความทั่วไปเด็ดขาด ต้องเป็น JSON เท่านั้น
        """

        print("🚀 เรียกใช้งาน OpenAI API...")
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"บอกข้อมูลเกี่ยวกับต้นไม้ {plant_name}"}
            ],
            max_tokens=500
        )

        print("✅ API call successful")
        result = (response.choices[0].message.content or "").strip()
        print(f"Raw response from OpenAI: {result}")

        # Parse คำตอบจาก OpenAI
        try:
            plant_info = json.loads(result)
            print("✅ JSON parsed successfully")
        except json.JSONDecodeError as e:
            print(f"❌ ไม่สามารถ parse JSON ได้: {e}")
            plant_info = {
                "name": "ไม่รู้จักต้นไม้",
                "price": "ไม่มีข้อมูล",
                "description": "ไม่มีข้อมูล",
                "careInstructions": "ไม่มีข้อมูล",
                "gardenIdeas": "ไม่มีข้อมูล"
            }
            print("🔧 Fallback to default plant info")

        # Mock data สำหรับดีล
        deals = [
            {"plant_name": plant_name, "shop_name": "ร้านต้นไม้ถูกใจ", "price": 600, "rating": 4.8, "link": "https://shopee.co.th/deal1"},
            {"plant_name": plant_name, "shop_name": "สวนสวย", "price": 750, "rating": 4.5, "link": "https://shopee.co.th/deal2"},
            {"plant_name": plant_name, "shop_name": "ร้านใบไม้", "price": 650, "rating": 4.7, "link": "https://shopee.co.th/deal3"}
        ]

        # หาดีลที่ดีที่สุด (ราคาถูกสุด และ rating สูง)
        best_deal = min(deals, key=lambda x: (x["price"], -x["rating"])) if deals else None

        if not best_deal:
            raise HTTPException(status_code=404, detail="No deals found")

        return {
            "plant_info": plant_info,
            "best_deal": {
                "plant_name": plant_name,
                "shop_name": best_deal["shop_name"],
                "price": best_deal["price"],
                "rating": best_deal["rating"],
                "link": best_deal["link"]
            },
            "related_deals": deals,
            "related_plants": [
                {"name": "ชบา (Hibiscus)", "price": "~150 บาท"},
                {"name": "ดอกเข็ม (Ixora)", "price": "~80 บาท"}
            ]
        }
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการค้นหา: {str(e)}")
        return {
            "plant_info": {
                "name": "ไม่รู้จักต้นไม้",
                "price": "ไม่มีข้อมูล",
                "description": "ไม่มีข้อมูล",
                "careInstructions": "ไม่มีข้อมูล",
                "gardenIdeas": "ไม่มีข้อมูล"
            },
            "best_deal": {
                "plant_name": plant_name,
                "shop_name": "ร้านต้นไม้ถูกใจ",
                "price": 600,
                "rating": 4.8,
                "link": "https://shopee.co.th/deal1"
            },
            "related_deals": [
                {"plant_name": plant_name, "shop_name": "ร้านต้นไม้ถูกใจ", "price": 600, "rating": 4.8, "link": "https://shopee.co.th/deal1"},
                {"plant_name": plant_name, "shop_name": "สวนสวย", "price": 750, "rating": 4.5, "link": "https://shopee.co.th/deal2"}
            ],
            "related_plants": [
                {"name": "ชบา (Hibiscus)", "price": "~150 บาท"},
                {"name": "ดอกเข็ม (Ixora)", "price": "~80 บาท"}
            ]
        }

async def get_popular_plants():
    try:
        plants = [
            {"name": "เฟื่องฟ้า", "shop_name": "ร้านต้นไม้ถูกใจ", "price": 120, "rating": 4.6, "link": "https://shopee.co.th/deal1"},
            {"name": "ลีลาวดี", "shop_name": "สวนลีลาวดี", "price": 80, "rating": 4.7, "link": "https://shopee.co.th/deal2"},
            {"name": "ชบา", "shop_name": "ร้านดอกชบา", "price": 130, "rating": 4.5, "link": "https://shopee.co.th/deal3"}
        ]
        return plants
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching popular plants: {str(e)}")

router.get("/popular-plants")(get_popular_plants)