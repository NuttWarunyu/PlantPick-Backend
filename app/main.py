import os
import uvicorn
from fastapi import FastAPI
from app.routers import upload, shopee, identify, search, generate_garden
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PlantPick API")

# Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS settings for Railway
origins = [
    "http://localhost:5173",  # Local development
    "https://plantpick-backend.up.railway.app",  # Replace with your Railway domain
    "https://plantpick.app",  # Custom domain (if set up)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(shopee.router, prefix="/shopee", tags=["Shopee"])
app.include_router(identify.router, tags=["Identify"])
app.include_router(search.router, tags=["Search"])
app.include_router(generate_garden.router, prefix="/garden", tags=["Garden"])  # Add prefix

if __name__ == "__main__":
    print("🚀 Railway is running `main.py`!")
    port = int(os.getenv("PORT", 8000))  # Ensure port is integer
    print(f"✅ Running on port: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)