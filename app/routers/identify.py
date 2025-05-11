import openai
import base64
import io
import os
import json
import re
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.routers.search import get_popular_plants
from PIL import Image
import requests
import time
import hashlib

# โหลดค่า API Key จาก .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY ยังไม่ถูกตั้งค่า")

router = APIRouter()

# ฟังก์ชันดึงข้อมูลจาก Shopee API
async def get_shopee_products(keyword: str, page: int = 0):
    APP_ID = "15394330041"
    SECRET = "IHYZSY7SCPNEYRSMPYSK2CKKYANVD5ZY"
    API_URL = "https://open-api.affiliate.shopee.co.th/graphql"

    query = """
    query Fetch($page: Int, $keyword: String) {
        productOfferV2(
            listType: 0,
            sortType: 2,
            page: $page,
            limit: 10,
            keyword: $keyword
        ) {
            nodes {
                commissionRate
                commission
                price
                productLink
                offerLink
            }
        }
    }
    """
    query = ' '.join(query.split())

    payload = {
        "query": query,
        "operationName": "Fetch",
        "variables": {
            "page": page,
            "keyword": keyword
        }
    }

    payload_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)

    timestamp = int(time.time())
    base_string = f"{APP_ID}{timestamp}{payload_str}{SECRET}"
    signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID},Timestamp={timestamp},Signature={signature}"
    }

    print(f"📦 Shopee API Request for '{keyword}': Payload={payload_str}, Signature={signature}")
    try:
        response = requests.post(API_URL, data=payload_str.encode("utf-8"), headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"📦 Shopee API Response for '{keyword}': {data}")
        if "errors" in data:
            print(f"❌ Shopee API Error for '{keyword}': {data['errors'][0]['message']}")
            return []
        return data["data"]["productOfferV2"]["nodes"]
    except Exception as e:
        print(f"❌ Shopee API Exception for '{keyword}': {str(e)}")
        return []

@router.post("/identify/")
async def analyze_image(file: UploadFile = File(None), name: str = Form(None)):
    try:
        print("📷 เริ่มวิเคราะห์...")
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        messages = []
        prompt = """
        คุณเป็นผู้เชี่ยวชาญด้านพืช ช่วยระบุต้นไม้และให้ข้อมูลตามฟิลด์ต่อไปนี้ในรูปแบบ JSON เท่านั้น (ห้ามใส่ข้อความอื่นนอกเหนือจาก JSON และต้องมีเครื่องหมาย {} เสมอ):

        {
          "name": "ชื่อต้นไม้ (ชื่อวิทยาศาสตร์) และลักษณะเด่น เช่น ดอกสีขาว (ถ้าระบุไม่ได้ให้ใส่ 'ไม่สามารถระบุได้')",
          "price": "ราคาโดยประมาณในหน่วยบาท เช่น ~100 บาท (ถ้าระบุไม่ได้ให้ใส่ 'ไม่มีข้อมูล')",
          "description": "ลักษณะของต้นไม้ เช่น ไม้พุ่มขนาดเล็ก สูง 2-3 เมตร (ถ้าระบุไม่ได้ให้ใส่ 'ไม่มีข้อมูล')",
          "careInstructions": "วิธีการดูแล เช่น รดน้ำสัปดาห์ละ 2 ครั้ง ชอบแดดจัด (ถ้าระบุไม่ได้ให้ใส่ 'ไม่มีข้อมูล')",
          "gardenIdeas": "เหมาะกับสวนสไตล์ไหน เช่น เหมาะกับสวนสไตล์เมดิเตอร์เรเนียน (ถ้าระบุไม่ได้ให้ใส่ 'ไม่มีข้อมูล')"
        }

        ตัวอย่าง:
        {
          "name": "ลีลาวดีสีขาว (Plumbago auriculata) ดอกสีขาว",
          "price": "~100 บาท",
          "description": "ไม้พุ่มขนาดเล็กถึงขนาดกลาง สูง 2-3 เมตร ดอกสีขาว",
          "careInstructions": "รดน้ำสัปดาห์ละ 2 ครั้ง ชอบแดดจัด",
          "gardenIdeas": "เหมาะกับสวนสไตล์เมดิเตอร์เรเนียน หรือจัดเป็นไม้พุ่มแนวรั้ว"
        }

        ห้ามตอบเป็นข้อความทั่วไปเด็ดขาด ต้องเป็น JSON เท่านั้น
        """

        image_base64 = None
        if file:
            print("📷 วิเคราะห์ภาพ...")
            image_bytes = await file.read()
            print(f"🔍 ขนาดภาพ (bytes): {len(image_bytes)}")
            image = Image.open(io.BytesIO(image_bytes))
            print("🖼️ เปิดภาพสำเร็จ")
            image = image.resize((300, 300))  # ลดขนาดเพื่อประหยัด Bandwidth
            print(f"🖼️ ขนาดภาพหลัง resize: {image.size}")

            # แปลงภาพเป็น Base64 เพื่อส่งกลับ
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            print(f"🔍 ขนาด Base64: {len(image_base64)}")

            messages = [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "ภาพนี้คือต้นอะไร?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ]
        elif name:
            print(f"📝 วิเคราะห์ชื่อ: {name}")
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"บอกข้อมูลเกี่ยวกับต้นไม้ {name}"}
            ]
        else:
            raise HTTPException(status_code=400, detail="ต้องส่งรูปหรือชื่อต้นไม้")

        print("🚀 เรียกใช้งาน OpenAI API...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500
        )

        print("✅ API call successful")
        result = response.choices[0].message.content.strip()
        print(f"Raw response from OpenAI: {result}")

        # ลบ Markdown Syntax (````json`) ก่อน Parse
        result = re.sub(r'^```json\s*|\s*```$', '', result, flags=re.MULTILINE).strip()
        print(f"Cleaned response for JSON parsing: {result}")

        # Parse คำตอบจาก OpenAI
        try:
            plant_info = json.loads(result)
            print("✅ JSON parsed successfully")
        except json.JSONDecodeError as e:
            print(f"❌ ไม่สามารถ parse JSON ได้: {e}")
            plant_info = {
                "name": "ไม่สามารถระบุได้",
                "price": "ไม่มีข้อมูล",
                "description": "ไม่มีข้อมูล",
                "careInstructions": "ไม่มีข้อมูล",
                "gardenIdeas": "ไม่มีข้อมูล"
            }
            print("🔧 Fallback to default plant info")

        # ดึงข้อมูลจาก Shopee API โดยใช้ชื่อที่ OpenAI ระบุ
        identified_name = plant_info.get("name", "")
        if identified_name and identified_name != "ไม่สามารถระบุได้":
            # ใช้เฉพาะชื่อต้นไม้ (ตัดส่วนลักษณะเด่นออก เช่น "ดอกสีฟ้า")
            search_name = re.split(r'\s*\(', identified_name)[0].strip()  # เช่น "พยับหมอก"
            print(f"🔍 เรียก Shopee API ด้วยชื่อ: {search_name}")
            shopee_products = await get_shopee_products(search_name)
            if shopee_products:
                cheapest_product = min(shopee_products, key=lambda x: float(x["price"]))
                plant_info["price"] = f"{cheapest_product['price']} บาท"
                plant_info["affiliateLink"] = cheapest_product["offerLink"]
            else:
                plant_info["price"] = "ไม่มีข้อมูล"
                plant_info["affiliateLink"] = "https://shopee.co.th/search?keyword=" + search_name
        else:
            plant_info["price"] = "ไม่มีข้อมูล"
            plant_info["affiliateLink"] = "https://shopee.co.th/plant-link"

        # ดึง Related Plants จาก Shopee API
        related_plants = []
        related_keywords = ["ไม้พุ่มดอกสีม่วง", "ไม้ประดับ"]  # สามารถปรับแต่ง Keyword ได้
        for related_keyword in related_keywords:
            related_products = await get_shopee_products(related_keyword)
            if related_products:
                cheapest_related = min(related_products, key=lambda x: float(x["price"]))
                related_plants.append({
                    "name": related_keyword,
                    "price": f"{cheapest_related['price']} บาท"
                })
            if len(related_plants) >= 2:  # จำกัดที่ 2 รายการ
                break
        if not related_plants:
            related_plants = [
                {"name": "ชบา (Hibiscus)", "price": "~150 บาท"},
                {"name": "ดอกเข็ม (Ixora)", "price": "~80 บาท"}
            ]
        print("🌱 Related plants added")

        return {
            "plant_info": plant_info,
            "related_plants": related_plants,
            "image_base64": image_base64  # ส่ง Base64 ของรูปกลับมา
        }

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return {
            "plant_info": {
                "name": "ไม่สามารถระบุได้",
                "price": "ไม่มีข้อมูล",
                "description": "ไม่มีข้อมูล",
                "careInstructions": "ไม่มีข้อมูล",
                "gardenIdeas": "ไม่มีข้อมูล",
                "affiliateLink": "https://shopee.co.th/plant-link"
            },
            "related_plants": [
                {"name": "ชบา (Hibiscus)", "price": "~150 บาท"},
                {"name": "ดอกเข็ม (Ixora)", "price": "~80 บาท"}
            ],
            "image_base64": None
        }

# ส่วน GET และ Popular Plants คงไว้ตามเดิม
@router.get("/identify/")
async def identify_plant_by_name(name: str = None):
    print("🚀 Entering GET /identify/ endpoint")
    try:
        print("📝 วิเคราะห์ชื่อ (GET):", name)
        if not name:
            print("⚠️ No name provided")
            raise HTTPException(status_code=400, detail="ต้องส่งชื่อต้นไม้")

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = """
        คุณเป็นผู้เชี่ยวชาญด้านพืช ช่วยระบุต้นไม้และให้ข้อมูลตามฟิลด์ต่อไปนี้ในรูปแบบ JSON เท่านั้น (ห้ามใส่ข้อความอื่นนอกเหนือจาก JSON และต้องมีเครื่องหมาย {} เสมอ):

        {
          "name": "ชื่อต้นไม้ (ชื่อวิทยาศาสตร์) และลักษณะเด่น เช่น ดอกสีขาว (ถ้าระบุไม่ได้ให้ใส่ 'ไม่สามารถระบุได้')",
          "price": "ราคาโดยประมาณในหน่วยบาท เช่น ~100 บาท (ถ้าระบุไม่ได้ให้ใส่ 'ไม่มีข้อมูล')",
          "description": "ลักษณะของต้นไม้ เช่น ไม้พุ่มขนาดเล็ก สูง 2-3 เมตร (ถ้าระบุไม่ได้ให้ใส่ 'ไม่มีข้อมูล')",
          "careInstructions": "วิธีการดูแล เช่น รดน้ำสัปดาห์ละ 2 ครั้ง ชอบแดดจัด (ถ้าระบุไม่ได้ให้ใส่ 'ไม่มีข้อมูล')",
          "gardenIdeas": "เหมาะกับสวนสไตล์ไหน เช่น เหมาะกับสวนสไตล์เมดิเตอร์เรเนียน (ถ้าระบุไม่ได้ให้ใส่ 'ไม่มีข้อมูล')"
        }

        ตัวอย่าง:
        {
          "name": "ลีลาวดีสีขาว (Plumbago auriculata) ดอกสีขาว",
          "price": "~100 บาท",
          "description": "ไม้พุ่มขนาดเล็กถึงขนาดกลาง สูง 2-3 เมตร ดอกสีขาว",
          "careInstructions": "รดน้ำสัปดาห์ละ 2 ครั้ง ชอบแดดจัด",
          "gardenIdeas": "เหมาะกับสวนสไตล์เมดิเตอร์เรเนียน หรือจัดเป็นไม้พุ่มแนวรั้ว"
        }

        ห้ามตอบเป็นข้อความทั่วไปเด็ดขาด ต้องเป็น JSON เท่านั้น
        """

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"บอกข้อมูลเกี่ยวกับต้นไม้ {name}"}
        ]

        print("🚀 เรียกใช้งาน OpenAI API (GET)...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500
        )

        print("✅ API call successful (GET)")
        result = response.choices[0].message.content.strip()
        print(f"Raw response from OpenAI (GET): {result}")

        # ลบ Markdown Syntax (````json`) ก่อน Parse
        result = re.sub(r'^```json\s*|\s*```$', '', result, flags=re.MULTILINE).strip()
        print(f"Cleaned response for JSON parsing (GET): {result}")

        # Parse คำตอบจาก OpenAI
        try:
            plant_info = json.loads(result)
            print("✅ JSON parsed successfully (GET)")
        except json.JSONDecodeError as e:
            print(f"❌ ไม่สามารถ parse JSON ได้ (GET): {e}")
            plant_info = {
                "name": "ไม่สามารถระบุได้",
                "price": "ไม่มีข้อมูล",
                "description": "ไม่มีข้อมูล",
                "careInstructions": "ไม่มีข้อมูล",
                "gardenIdeas": "ไม่มีข้อมูล"
            }
            print("🔧 Fallback to default plant info (GET)")

        # ดึงข้อมูลจาก Shopee API
        identified_name = plant_info.get("name", "")
        if identified_name and identified_name != "ไม่สามารถระบุได้":
            search_name = re.split(r'\s*\(', identified_name)[0].strip()  # เช่น "พยับหมอก"
            print(f"🔍 เรียก Shopee API ด้วยชื่อ: {search_name}")
            shopee_products = await get_shopee_products(search_name)
            if shopee_products:
                cheapest_product = min(shopee_products, key=lambda x: float(x["price"]))
                plant_info["price"] = f"{cheapest_product['price']} บาท"
                plant_info["affiliateLink"] = cheapest_product["offerLink"]
            else:
                plant_info["price"] = "ไม่มีข้อมูล"
                plant_info["affiliateLink"] = "https://shopee.co.th/search?keyword=" + search_name
        else:
            plant_info["price"] = "ไม่มีข้อมูล"
            plant_info["affiliateLink"] = "https://shopee.co.th/plant-link"

        # ดึง Related Plants จาก Shopee API
        related_plants = []
        related_keywords = ["ไม้พุ่มดอกสีม่วง", "ไม้ประดับ"]  # สามารถปรับแต่ง Keyword ได้
        for related_keyword in related_keywords:
            related_products = await get_shopee_products(related_keyword)
            if related_products:
                cheapest_related = min(related_products, key=lambda x: float(x["price"]))
                related_plants.append({
                    "name": related_keyword,
                    "price": f"{cheapest_related['price']} บาท"
                })
            if len(related_plants) >= 2:  # จำกัดที่ 2 รายการ
                break
        if not related_plants:
            related_plants = [
                {"name": "ชบา (Hibiscus)", "price": "~150 บาท"},
                {"name": "ดอกเข็ม (Ixora)", "price": "~80 บาท"}
            ]
        print("🌱 Related plants added (GET)")

        print("✅ Returning response from GET /identify/")
        return {
            "plant_info": plant_info,
            "related_plants": related_plants,
            "image_base64": None  # ไม่มีรูปใน GET
        }

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด (GET): {str(e)}")
        return {
            "plant_info": {
                "name": "ไม่สามารถระบุได้",
                "price": "ไม่มีข้อมูล",
                "description": "ไม่มีข้อมูล",
                "careInstructions": "ไม่มีข้อมูล",
                "gardenIdeas": "ไม่มีข้อมูล",
                "affiliateLink": "https://shopee.co.th/plant-link"
            },
            "related_plants": [
                {"name": "ชบา (Hibiscus)", "price": "~150 บาท"},
                {"name": "ดอกเข็ม (Ixora)", "price": "~80 บาท"}
            ],
            "image_base64": None
        }

@router.get("/popular-plants")
async def popular_plants():
    try:
        plants = await get_popular_plants()
        return plants
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching popular plants: {str(e)}")