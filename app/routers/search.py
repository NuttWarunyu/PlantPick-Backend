import os
import json
import re
from openai import AsyncOpenAI
from fastapi import HTTPException, APIRouter, Query

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
router = APIRouter()

async def identify_plant(image_data: bytes):
    try:
        response = await client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "ช่วยระบุว่าต้นไม้นี้คือต้นอะไร และให้ข้อมูลเกี่ยวกับต้นไม้ รวมถึงการดูแลและไอเดียจัดสวนด้วย"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data.decode('utf-8')}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error identifying plant: {str(e)}")

@router.get("/search-by-name")
async def search_by_name(plant_name: str = Query(..., alias="name")):
    try:
        print(f"🔍 เริ่มค้นหาดีลต้นไม้: {plant_name}")
        # Mock data สำหรับดีล (ในอนาคตให้ดึงจาก database หรือ API)
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
            "best_deal": {
                "plant_name": plant_name,
                "shop_name": best_deal["shop_name"],
                "price": best_deal["price"],
                "rating": best_deal["rating"],
                "link": best_deal["link"]
            },
            "related_deals": deals
        }
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการค้นหา: {str(e)}")
        return {
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