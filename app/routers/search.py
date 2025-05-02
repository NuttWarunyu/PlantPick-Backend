import os
import json
import re
from openai import AsyncOpenAI
from fastapi import HTTPException, APIRouter

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

async def search_by_name(plant_name: str):
    try:
        print(f"🔍 เริ่มค้นหาข้อมูลต้นไม้: {plant_name}")
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": f"ช่วยบอกข้อมูลเกี่ยวกับต้นไม้ชื่อ '{plant_name}' ในประเทศไทย รวมถึง:\n- ลักษณะ (description)\n- วิธีดูแล (careInstructions)\n- ไอเดียจัดสวน (gardenIdeas)\n- ราคาเฉลี่ย (price) ในหน่วยบาท\nตอบในรูปแบบข้อความสั้น ๆ และชัดเจน"
                }
            ],
            max_tokens=300,
        )
        plant_info_raw = response.choices[0].message.content
        print(f"Raw response from OpenAI: {plant_info_raw}")

        # แยกข้อมูลจากข้อความของ OpenAI
        plant_info = {
            "name": plant_name,
            "description": re.search(r"ลักษณะ:(.+?)(?=วิธีดูแล|$)", plant_info_raw, re.DOTALL) or "ไม่มีข้อมูล",
            "careInstructions": re.search(r"วิธีดูแล:(.+?)(?=ไอเดียจัดสวน|$)", plant_info_raw, re.DOTALL) or "ไม่มีข้อมูล",
            "gardenIdeas": re.search(r"ไอเดียจัดสวน:(.+?)(?=ราคาเฉลี่ย|$)", plant_info_raw, re.DOTALL) or "ไม่มีข้อมูล",
            "price": re.search(r"ราคาเฉลี่ย:(.+?)$", plant_info_raw) or "~ไม่มีข้อมูล",
            "affiliateLink": "https://shopee.co.th/plant-link"
        }
        for key, value in plant_info.items():
            if isinstance(value, re.Match):
                plant_info[key] = value.group(1).strip() if value.group(1) else "ไม่มีข้อมูล"
            else:
                plant_info[key] = value

        # เพิ่ม related plants (สมมติ)
        related_plants = [
            {"name": "ยางอินเดีย", "price": "~200 บาท"},
            {"name": "มอนสเตร่า", "price": "~500 บาท"}
        ]

        return {
            "plant_info": plant_info,
            "related_plants": related_plants
        }
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการค้นหา: {str(e)}")
        return {
            "plant_info": {
                "name": plant_name,
                "description": "ไม่มีข้อมูล",
                "careInstructions": "ไม่มีข้อมูล",
                "gardenIdeas": "ไม่มีข้อมูล",
                "price": "ไม่มีข้อมูล",
                "affiliateLink": "https://shopee.co.th/plant-link"
            },
            "related_plants": [
                {"name": "ยางอินเดีย", "price": "~200 บาท"},
                {"name": "มอนสเตร่า", "price": "~500 บาท"}
            ]
        }

# กำหนด route สำหรับ search_by_name
router.get("/search-by-name/{plant_name}")(search_by_name)

async def get_popular_plants():
    try:
        # ใช้ mock data แทนการเรียก OpenAI
        plants = [
            {"name": "เฟื่องฟ้า", "price": "~120 บาท", "description": "ไม้เลื้อย ดอกสีสดใส"},
            {"name": "ลีลาวดี", "price": "~80 บาท", "description": "ไม้ยืนต้น ดอกหอม"},
            {"name": "ชบา", "price": "~130 บาท", "description": "ไม้พุ่ม ดอกสีแดง"}
        ]

        shop_data = [
            {
                "shopName": "ร้านต้นไม้ถูกใจ",
                "price": "~120 บาท",
                "shippingTime": "จัดส่งภายใน 1-2 วัน",
                "link": "https://shopee.co.th/search?keyword=เฟื่องฟ้า"
            },
            {
                "shopName": "สวนลีลาวดี",
                "price": "~80 บาท",
                "shippingTime": "จัดส่งภายใน 1 วัน",
                "link": "https://shopee.co.th/search?keyword=ลีลาวดี"
            },
            {
                "shopName": "ร้านดอกชบา",
                "price": "~130 บาท",
                "shippingTime": "จัดส่งภายใน 1-2 วัน",
                "link": "https://shopee.co.th/search?keyword=ชบา"
            }
        ]

        for i, plant in enumerate(plants):
            if i < len(shop_data):
                plant.update(shop_data[i])

        return plants
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching popular plants: {str(e)}")

router.get("/popular-plants")(get_popular_plants)