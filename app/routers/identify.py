import openai
import base64
import io
import os
import json
import re
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File
from PIL import Image

# โหลดค่า API Key จาก .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY ยังไม่ถูกตั้งค่า")

router = APIRouter()

@router.post("/identify/")
async def analyze_image(file: UploadFile = File(...)):
    try:
        print("📷 เริ่มวิเคราะห์ภาพ...")
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        image = image.resize((300, 300))  # ลดขนาดเพื่อประหยัด Bandwidth

        # แปลงภาพเป็น Base64
        print("🔄 แปลงรูปเป็น Base64...")
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # ✅ ใช้ OpenAI API Client ตามเวอร์ชันใหม่
        print("🚀 เรียกใช้งาน OpenAI API...")
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        # ปรับ prompt ให้ OpenAI ตอบกลับในรูปแบบ JSON เท่านั้น
        prompt = """
        คุณเป็นผู้เชี่ยวชาญด้านพืช ช่วยระบุต้นไม้ในภาพนี้และให้ข้อมูลตามฟิลด์ต่อไปนี้ในรูปแบบ JSON เท่านั้น (ห้ามใส่ข้อความอื่นนอกเหนือจาก JSON และต้องมีเครื่องหมาย {} เสมอ):

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

        ถ้าระบุต้นไม้ไม่ได้ ให้ตอบกลับ:
        {
          "name": "ไม่สามารถระบุได้",
          "price": "ไม่มีข้อมูล",
          "description": "ไม่มีข้อมูล",
          "careInstructions": "ไม่มีข้อมูล",
          "gardenIdeas": "ไม่มีข้อมูล"
        }

        ห้ามตอบเป็นข้อความทั่วไปเด็ดขาด ต้องเป็น JSON เท่านั้น
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "ภาพนี้คือต้นอะไร?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=500
        )

        print("✅ API call successful")
        result = response.choices[0].message.content.strip()
        print(f"Raw response from OpenAI: {result}")

        # Parse คำตอบจาก OpenAI
        try:
            plant_info = json.loads(result)
        except json.JSONDecodeError:
            print("❌ ไม่สามารถ parse JSON ได้")
            # ถ้าไม่ใช่ JSON ให้พยายามแปลง string เป็น JSON object
            if "ไม่สามารถระบุ" in result or result.strip() == "":
                plant_info = {
                    "name": "ไม่สามารถระบุได้",
                    "price": "ไม่มีข้อมูล",
                    "description": "ไม่มีข้อมูล",
                    "careInstructions": "ไม่มีข้อมูล",
                    "gardenIdeas": "ไม่มีข้อมูล"
                }
            else:
                # พยายามดึงข้อมูลจาก string
                name_match = re.search(r"นี่คือต้น(.+?)(?:[.,\s]|$)", result) or re.search(r"(.+?)เป็นไม้", result)
                description_match = re.search(r"เป็นไม้.+?(?=###|$)", result)
                care_instructions_match = re.search(r"### การดูแลต้น.+?แสงแดด.+?(?=เหมาะสำหรับ|$)", result, re.DOTALL)
                garden_ideas_match = re.search(r"เหมาะสำหรับ(.+?)(?:ค่ะ|$)", result)

                plant_info = {
                    "name": name_match.group(1).strip() if name_match else "ไม่สามารถระบุได้",
                    "price": "ไม่มีข้อมูล",  # OpenAI ไม่ได้ให้ราคา
                    "description": description_match.group(0).strip() if description_match else "ไม่มีข้อมูล",
                    "careInstructions": care_instructions_match.group(0).replace("### การดูแลต้น", "").strip() if care_instructions_match else "ไม่มีข้อมูล",
                    "gardenIdeas": garden_ideas_match.group(1).strip() if garden_ideas_match else "ไม่มีข้อมูล"
                }

        # เพิ่ม affiliateLink (สมมติ)
        plant_info["affiliateLink"] = "https://shopee.co.th/plant-link"

        # เพิ่ม related_plants (สมมติ)
        related_plants = [
            {"name": "ชบา (Hibiscus)", "price": "~150 บาท"},
            {"name": "ดอกเข็ม (Ixora)", "price": "~80 บาท"}
        ]

        return {
            "plant_info": plant_info,
            "related_plants": related_plants
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
            ]
        }