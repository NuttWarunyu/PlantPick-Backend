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

@router.get("/search-by-name")  # ผูกกับฟังก์ชันทันที
async def search_by_name(plant_name: str):
    try:
        print(f"🔍 เริ่มค้นหาข้อมูลต้นไม้: {plant_name}")
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": f"ช่วยบอกข้อมูลเกี่ยวกับต้นไม้ชื่อ '{plant_name}' ในประเทศไทย โดยตอบในรูปแบบ JSON เท่านั้น:\n{{\n  \"description\": \"<ลักษณะ>\",\n  \"careInstructions\": \"<วิธีดูแล>\",\n  \"gardenIdeas\": \"<ไอเดียจัดสวน>\",\n  \"price\": \"<ราคาเฉลี่ย>\"\n}}"
                }
            ],
            max_tokens=300,
        )
        plant_info_raw = response.choices[0].message.content
        print(f"Raw response from OpenAI: {plant_info_raw}")

        # ทำความสะอาดข้อมูลก่อน parse
        cleaned_response = plant_info_raw.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # ตัด ```json ออก
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # ตัด ``` ออก
        cleaned_response = cleaned_response.strip()

        # ถ้ายังมีข้อความนอก JSON ตัดออกให้เหลือเฉพาะส่วนที่เป็น JSON
        json_start = cleaned_response.find("{")
        json_end = cleaned_response.rfind("}") + 1
        if json_start != -1 and json_end != -1:
            cleaned_response = cleaned_response[json_start:json_end]

        # Parse JSON
        try:
            plant_info = json.loads(cleaned_response)
            plant_info["name"] = plant_name
            plant_info["affiliateLink"] = "https://shopee.co.th/plant-link"
        except json.JSONDecodeError as e:
            print(f"❌ ไม่สามารถ parse JSON ได้: {e}")
            plant_info = {
                "name": plant_name,
                "description": "ไม่มีข้อมูล",
                "careInstructions": "ไม่มีข้อมูล",
                "gardenIdeas": "ไม่มีข้อมูล",
                "price": "~ไม่มีข้อมูล",
                "affiliateLink": "https://shopee.co.th/plant-link"
            }

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
                "description": "ไม้ประดับขนาดกลางถึงใหญ่ ใบใหญ่หนาและมันวาว",
                "careInstructions": "รดน้ำสัปดาห์ละ 1-2 ครั้ง ชอบแสงแดดปานกลาง",
                "gardenIdeas": "เหมาะสำหรับจัดสวนในบ้านหรือสำนักงาน",
                "price": "~300-1000 บาท",
                "affiliateLink": "https://shopee.co.th/plant-link"
            },
            "related_plants": [
                {"name": "ยางอินเดีย", "price": "~200 บาท"},
                {"name": "มอนสเตร่า", "price": "~500 บาท"}
            ]
        }

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