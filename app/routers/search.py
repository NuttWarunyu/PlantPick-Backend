import os
import json
import re
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
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": "ช่วยบอกชื่อต้นไม้ยอดนิยม 3 อันดับในประเทศไทย พร้อมลักษณะ ราคาเฉลี่ย และเหตุผลที่คนนิยมปลูก โดยตอบในรูปแบบ JSON ดังนี้:\n[\n  {\"name\": \"ชื่อต้นไม้\", \"description\": \"ลักษณะ\", \"price\": \"ราคา ~xxx บาท\", \"reason\": \"เหตุผลที่นิยม\"},\n  {\"name\": \"ชื่อต้นไม้\", \"description\": \"ลักษณะ\", \"price\": \"ราคา ~xxx บาท\", \"reason\": \"เหตุผลที่นิยม\"},\n  {\"name\": \"ชื่อต้นไม้\", \"description\": \"ลักษณะ\", \"price\": \"ราคา ~xxx บาท\", \"reason\": \"เหตุผลที่นิยม\"}\n]"
                }
            ],
            max_tokens=300,
        )
        popular_plants_info = response.choices[0].message.content

        # Debug: ดูข้อมูลดิบจาก OpenAI
        print("Raw response from OpenAI:", popular_plants_info)

        # ล้าง ```json และ ``` ออก
        cleaned_response = popular_plants_info.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # ลบ ```json ออก
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # ลบ ``` ออก
        cleaned_response = cleaned_response.strip()

        # ล้างตัวอักษรพิเศษหลัง ] โดยใช้ regex
        cleaned_response = re.sub(r'\][\s\S]*', ']', cleaned_response)

        # ซ่อม JSON ที่ไม่สมบูรณ์
        # 1. ตรวจสอบว่า string ปิดครบหรือไม่
        if cleaned_response.count('"') % 2 != 0:  # ถ้าจำนวน " ไม่ครบคู่
            last_quote_index = cleaned_response.rfind('"')
            cleaned_response = cleaned_response[:last_quote_index] + '"}]'  # เพิ่ม "}] ปิดท้าย

        # 2. ตรวจสอบว่า JSON ปิดครบหรือไม่
        if not cleaned_response.endswith(']'):
            cleaned_response = cleaned_response + ']'
        if not cleaned_response.endswith('}'):
            if cleaned_response.endswith(']'):
                cleaned_response = cleaned_response[:-1] + '}]'
            else:
                cleaned_response = cleaned_response + '}]'

        try:
            # Parse JSON จาก OpenAI
            plants = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print("Using mock data as fallback")
            plants = [
                {"name": "เฟื่องฟ้า", "price": "~120 บาท", "description": "ไม้เลื้อย ดอกสีสดใส"},
                {"name": "ลีลาวดี", "price": "~80 บาท", "description": "ไม้ยืนต้น ดอกหอม"},
                {"name": "ชบา", "price": "~130 บาท", "description": "ไม้พุ่ม ดอกสีแดง"}
            ]

        # Debug: ดูว่า plants มีอะไรหลังจาก parse
        print("Parsed plants:", plants)

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