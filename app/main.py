import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

from app.routers import upload, shopee, identify, search, generate_garden, garden_controlnet_test

# Load .env variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="PlantPick API")

# Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS settings (for production + dev)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*plantpick\.app|http://localhost:5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(shopee.router, prefix="/shopee", tags=["Shopee"])
app.include_router(identify.router, tags=["Identify"])
app.include_router(search.router, tags=["Search"])
app.include_router(generate_garden.router, prefix="/garden", tags=["Garden"])
app.include_router(garden_controlnet_test.router, prefix="/garden-test")

# Run locally (optional)
if __name__ == "__main__":
    print("🚀 Railway is running `main.py`!")
    port = int(os.getenv("PORT", 8000))
    print(f"✅ Running on port: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)