from fastapi import APIRouter
import httpx
import time
import json
import hashlib
import hmac
import os

router = APIRouter()

# Hardcode สำหรับทดสอบ
APP_ID = "15394330041"
SECRET = "REM67QXPPTX5G7VE3OJGHHUVYE74HAOI"

# หรือใช้ environment variables ถ้ามี
# APP_ID = os.getenv("SHOPEE_APP_ID") or "15394330041"
# SECRET = os.getenv("SHOPEE_SECRET_KEY") or "REM67QXPPTX5G7VE3OJGHHUVYE74HAOI"
# ลองใช้ API version ใหม่
API_URL = "https://open-api.affiliate.shopee.co.th/graphql"
# หรือลองใช้ API version ใหม่
# API_URL = "https://open-api.affiliate.shopee.co.th/graphql/v2"

async def get_shopee_products(keyword: str, page: int = 0):
    if not APP_ID or not SECRET:
        print("❌ Shopee APP_ID or SECRET_KEY is not set.")
        return []

    # ✅ GraphQL query - ใช้แบบเดียวกับที่ทำงานได้
    query = """
    {
        productOfferV2() {
            nodes {
                productName
                itemId
                commissionRate
                commission
                price
                sales
                imageUrl
                shopName
                productLink
                offerLink
                periodStartTime
                periodEndTime
                priceMin
                priceMax
                productCatIds
                ratingStar
                priceDiscountRate
                shopId
                shopType
                sellerCommissionRate
                shopeeCommissionRate
            }
            pageInfo {
                page
                limit
                hasNextPage
                scrollId
            }
        }
    }
    """.strip()

    # ✅ ไม่ต้องใช้ variables แล้ว
    payload = {
        "query": query
    }

    # ✅ JSON แบบ compact สำหรับสร้าง signature
    payload_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    
    # ใช้ seconds (ไม่ใช่ milliseconds) และทำให้ fresh
    timestamp = int(time.time())  # seconds
    
    # ✅ ใช้ HMAC-SHA256 แทน SHA256
    signature = hmac.new(
        SECRET.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    # หรือลองใช้ format แบบอื่น
    # base_string = f"{timestamp}{APP_ID}{payload_str}{SECRET}"
    # signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    
    # หรือลองใช้ format แบบอื่น
    # base_string = f"{APP_ID}{SECRET}{timestamp}{payload_str}"
    # signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    
    # หรือลองใช้ format แบบอื่น
    # base_string = f"{APP_ID}{SECRET}{payload_str}{timestamp}"
    # signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    
    # หรือลองใช้ format แบบอื่น
    # base_string = f"{timestamp}{APP_ID}{payload_str}{SECRET}"
    # signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    
    # หรือลองใช้ format แบบอื่น
    # base_string = f"{APP_ID}{SECRET}{timestamp}{payload_str}"
    # signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    
    # หรือลองใช้ format แบบอื่น
    # base_string = f"{timestamp}{APP_ID}{payload_str}{SECRET}"
    # signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    
    # หรือลองใช้ format แบบอื่น
    # base_string = f"{APP_ID}{SECRET}{timestamp}{payload_str}"
    # signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    
    # Debug log
    print(f"🔍 Debug Shopee API:")
    print(f"   APP_ID: {APP_ID}")
    print(f"   Timestamp: {timestamp}")
    print(f"   Payload: {payload_str[:100]}...")
    print(f"   Signature: {signature}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 {signature}",
        "X-TIMESTAMP": str(timestamp),
        "X-PARTNER-ID": APP_ID,
        "User-Agent": "PlantPick-Bot/1.0"
    }
    
    # หรือลองใช้ format แบบอื่น
    # headers = {
    #     "Content-Type": "application/json",
    #     "Authorization": f"SHA256 Credential={APP_ID},Timestamp={timestamp},Signature={signature}",
    #     "Accept": "application/json"
    # }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()

        data = response.json()
        # print(f"📦 Shopee API Response for '{keyword}': {json.dumps(data, indent=2, ensure_ascii=False)}")

        if "errors" in data:
            print(f"❌ Shopee API Error: {data['errors'][0]['message']}")
            return []

        return data.get("data", {}).get("productOfferV2", {}).get("nodes", [])

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return []

@router.post("/shopee-products")
async def get_shopee_products_endpoint(data: dict):
    keyword = data.get("keyword", "")
    page = data.get("page", 0)
    return await get_shopee_products(keyword, page)

@router.get("/test-shopee-api")
async def test_shopee_api_endpoint():
    """
    ทดสอบ Shopee API เพื่อตรวจสอบ credentials
    """
    if not APP_ID or not SECRET:
        return {"error": "APP_ID หรือ SECRET ไม่ถูกตั้งค่า"}
    
    # ทดสอบด้วย keyword ง่ายๆ
    products = await get_shopee_products("ต้นไม้", 0)
    
    if products:
        return {
            "status": "success",
            "message": f"พบสินค้า {len(products)} รายการ",
            "sample_product": products[0] if products else None
        }
    else:
        return {
            "status": "error",
            "message": "ไม่พบสินค้าหรือ API error",
            "debug_info": {
                "app_id": APP_ID,
                "secret_length": len(SECRET) if SECRET else 0
            }
        }