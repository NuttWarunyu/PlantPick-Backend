import os
from openai import AsyncOpenAI
from fastapi import HTTPException

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": f"ช่วยบอกข้อมูลเกี่ยวกับต้นไม้ชื่อ '{plant_name}' รวมถึงลักษณะ วิธีดูแล ไอเดียจัดสวน และราคาเฉลี่ยในประเทศไทย"
                }
            ],
            max_tokens=300,
        )
        plant_info = response.choices[0].message.content

        related_plants = [
            {"name": "ต้นโมก", "price": "~200 บาท"},
            {"name": "ต้นเข็ม", "price": "~80 บาท"},
        ]

        return {
            "plant_info": {
                "name": plant_name,
                "description": plant_info,
                "price": "ราคาเฉลี่ย: ~150 บาท (ขึ้นอยู่กับขนาดและร้านค้า)",
            },
            "related_plants": related_plants
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching plant by name: {str(e)}")

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