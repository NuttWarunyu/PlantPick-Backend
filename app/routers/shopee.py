from fastapi import APIRouter
import requests
import os

router = APIRouter()
SHOPEE_API_KEY = os.getenv("SHOPEE_API_KEY")

@router.get("/search")
async def search_shopee(q: str):
    url = f"https://shopee-api.com/search?query={q}&api_key={SHOPEE_API_KEY}"
    response = requests.get(url)
    return response.json()