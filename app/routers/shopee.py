from fastapi import APIRouter
import requests
import time
import json
import hashlib

router = APIRouter()

APP_ID = "15394330041"
SECRET = "IHYZSY7SCPNEYRSMPYSK2CKKYANVD5ZY"
API_URL = "https://open-api.affiliate.shopee.co.th/graphql"

@router.post("/shopee-products")
async def get_shopee_products(data: dict):
    keyword = data.get("keyword", "")
    page = data.get("page", 0)

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

    print("Payload:", payload_str)
    print("Signature:", signature)
    print("Headers:", headers)

    try:
        # ❗ send raw string to ensure consistency
        response = requests.post(API_URL, data=payload_str.encode("utf-8"), headers=headers)
        response.raise_for_status()
        data = response.json()
        print("Shopee API Response:", data)

        if "errors" in data:
            return {"error": data["errors"][0]["message"]}
        return data["data"]["productOfferV2"]["nodes"]
    except Exception as e:
        return {"error": str(e)}