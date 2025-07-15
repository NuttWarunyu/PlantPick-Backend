from fastapi import APIRouter
import httpx # <-- 1. เปลี่ยนมาใช้ httpx
import time
import json
import hashlib
import os

router = APIRouter()

# === 2. อ่านค่าจาก Environment Variables เพื่อความปลอดภัย ===
APP_ID = os.getenv("SHOPEE_APP_ID")
SECRET = os.getenv("SHOPEE_SECRET_KEY")
API_URL = "https://open-api.affiliate.shopee.co.th/graphql"

# === 3. เปลี่ยนฟังก์ชันทั้งหมดให้เป็น async และใช้ httpx ===
async def get_shopee_products(keyword: str, page: int = 0):
    if not APP_ID or not SECRET:
        print("❌ Shopee APP_ID or SECRET_KEY is not set on the server.")
        return []

    query = """
    query Fetch($page: Int, $keyword: String) {
        productOfferV2(listType: 0, sortType: 2, page: $page, limit: 10, keyword: $keyword) {
            nodes { commissionRate commission price productLink offerLink }
        }
    }
    """
    query = ' '.join(query.split())

    payload = {
        "query": query,
        "operationName": "Fetch",
        "variables": { "page": page, "keyword": keyword }
    }

    # เราจะใช้ payload ที่เป็น Dictionary โดยตรงสำหรับ httpx
    # แต่ยังคงต้องสร้าง string สำหรับ Signature
    payload_str_for_signature = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    timestamp = int(time.time())
    base_string = f"{APP_ID}{timestamp}{payload_str_for_signature}{SECRET}"
    signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID},Timestamp={timestamp},Signature={signature}"
    }

    try:
        # ใช้ httpx.AsyncClient() สำหรับการส่งคำขอแบบ async
        async with httpx.AsyncClient() as client:
            # ใช้ json=payload เพื่อให้ httpx จัดการการส่งข้อมูล JSON ให้ถูกต้อง
            response = await client.post(API_URL, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status() # จะโยน Error ถ้า status code ไม่ใช่ 2xx
        
        data = response.json()
        print(f"📦 Shopee API Response for '{keyword}': {data}")

        if "errors" in data:
            print(f"❌ Shopee API Error for '{keyword}': {data['errors'][0]['message']}")
            return []
        
        return data.get("data", {}).get("productOfferV2", {}).get("nodes", [])

    except httpx.HTTPStatusError as e:
        print(f"❌ Shopee API HTTP Status Error for '{keyword}': {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        print(f"❌ Shopee API Exception for '{keyword}': {str(e)}")
        return []

# (Endpoint นี้ไม่จำเป็นต้องมี ถ้าเราเรียกใช้ฟังก์ชันโดยตรงจาก router อื่น)
# แต่จะคงไว้เผื่อคุณต้องการทดสอบโดยตรง
@router.post("/shopee-products")
async def get_shopee_products_endpoint(data: dict):
    keyword = data.get("keyword", "")
    page = data.get("page", 0)
    return await get_shopee_products(keyword, page)
