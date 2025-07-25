#!/usr/bin/env python3
"""
ทดสอบ Shopee Affiliate API
"""
import os
import time
import json
import hashlib
import httpx
from dotenv import load_dotenv

load_dotenv()

# ข้อมูลจาก environment
APP_ID = os.getenv("SHOPEE_APP_ID")
SECRET = os.getenv("SHOPEE_SECRET_KEY")
API_URL = "https://open-api.affiliate.shopee.co.th/graphql"

def test_shopee_api():
    print("🧪 ทดสอบ Shopee Affiliate API")
    print(f"APP_ID: {APP_ID}")
    if SECRET:
        print(f"SECRET: {SECRET[:10]}...{SECRET[-10:]}")
    else:
        print("SECRET: None")
    print("-" * 50)
    
    if not APP_ID or not SECRET:
        print("❌ APP_ID หรือ SECRET ไม่ถูกตั้งค่า")
        return False
    
    # GraphQL query
    query = """
    query Fetch($keyword: String!, $page: Int!) {
        productOfferV2(listType: 0, sortType: 2, page: $page, limit: 5, keyword: $keyword) {
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
    
    variables = {
        "keyword": "ต้นไม้",
        "page": 0
    }
    
    payload = {
        "query": query,
        "operationName": "Fetch",
        "variables": variables
    }
    
    # สร้าง signature
    payload_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    timestamp = int(time.time())
    base_string = f"{APP_ID}{timestamp}{payload_str}{SECRET}"
    signature = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID},Timestamp={timestamp},Signature={signature}"
    }
    
    print(f"📤 ส่ง Request:")
    print(f"   URL: {API_URL}")
    print(f"   Timestamp: {timestamp}")
    print(f"   Signature: {signature}")
    print(f"   Payload: {payload_str[:100]}...")
    print("-" * 50)
    
    try:
        response = httpx.post(API_URL, headers=headers, json=payload, timeout=10)
        print(f"📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📥 Response Body: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if "errors" in data:
                print(f"❌ API Error: {data['errors']}")
                return False
            elif "data" in data:
                products = data.get("data", {}).get("productOfferV2", {}).get("nodes", [])
                print(f"✅ สำเร็จ! พบสินค้า {len(products)} รายการ")
                return True
            else:
                print(f"❓ Response ไม่มี data หรือ errors")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_shopee_api()
    if success:
        print("\n🎉 Shopee API ทำงานได้ปกติ!")
    else:
        print("\n💥 Shopee API มีปัญหา!") 