from fastapi import APIRouter
import httpx
import time
import json
import hashlib
import os

router = APIRouter()

APP_ID = os.getenv("SHOPEE_APP_ID")
SECRET = os.getenv("SHOPEE_SECRET_KEY")
API_URL = "https://open-api.affiliate.shopee.co.th/graphql"

async def get_shopee_products(keyword: str, page: int = 0):
    if not APP_ID or not SECRET:
        print("❌ Shopee APP_ID or SECRET_KEY is not set.")
        return []

    # ✅ GraphQL query
    query = """
    query Fetch($keyword: String!, $page: Int!) {
        productOfferV2(listType: 0, sortType: 2, page: $page, limit: 10, keyword: $keyword) {
            nodes {
                commissionRate
                commission
                price
                productLink
                offerLink
            }
        }
    }
    """.strip()

    # ✅ ส่ง variables เป็น dict (object) เท่านั้น
    variables = {
        "keyword": keyword,
        "page": page
    }

    payload = {
        "query": query,
        "operationName": "Fetch",
        "variables": variables  # ✅ ต้องเป็น dict, ห้าม json.dumps
    }

    # ✅ JSON แบบ compact สำหรับสร้าง signature
    payload_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    timestamp = int(time.time())
    base_string = f"{APP_ID}{timestamp}{payload_str}{SECRET}"
    signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID},Timestamp={timestamp},Signature={signature}"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()

        data = response.json()
        print(f"📦 Shopee API Response for '{keyword}': {json.dumps(data, indent=2, ensure_ascii=False)}")

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