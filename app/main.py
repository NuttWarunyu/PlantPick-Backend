import os
import uvicorn
from fastapi import FastAPI
from app.routers import upload, shopee, identify, search, generate_garden, plant_doctor, admin
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="PlantPick - AI จัดสวน API",
    description="API สำหรับบริการ AI จัดสวน ออกแบบสวนในฝันด้วยปัญญาประดิษฐ์",
    version="1.0.0",
    contact={
        "name": "PlantPick Support",
        "email": "support@plantpick.ai",
    },
    license_info={
        "name": "MIT",
    },
)

# Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS settings for Railway
origins = [
    "http://localhost:5173",  # Local development
    "https://plantpick.app",  # Frontend production domain
    "https://plantpick.ai",   # Main domain
    "https://www.plantpick.ai", # www subdomain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],  # จำกัด methods ที่ใช้จริง
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],  # จำกัด headers ที่ใช้จริง
)

# Include Routers
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(shopee.router, prefix="/shopee", tags=["Shopee"])  # มี prefix
app.include_router(identify.router, tags=["Identify"])
app.include_router(search.router, tags=["Search"])
app.include_router(generate_garden.router, prefix="/garden", tags=["Garden"])  # Add prefix
from app.routers import analyze_garden
app.include_router(analyze_garden.router, tags=["AnalyzeGarden"])
app.include_router(plant_doctor.router, tags=["Plant Doctor"])  # Add Plant Doctor router
app.include_router(admin.router, prefix="/admin", tags=["Admin"])  # Add Admin router

# SEO and Health Check Endpoints
@app.get("/", tags=["SEO"])
async def root():
    """Root endpoint for SEO and health check"""
    return {
        "message": "PlantPick - AI จัดสวน API",
        "description": "บริการ AI จัดสวน ออกแบบสวนในฝันด้วยปัญญาประดิษฐ์",
        "version": "1.0.0",
        "status": "healthy",
        "services": [
            "AI ออกแบบสวน",
            "AI หมอต้นไม้",
            "วิเคราะห์ภาพสวน",
            "ประเมินงบประมาณ",
            "ค้นหาพรรณไม้"
        ]
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "PlantPick API"}

@app.get("/robots.txt", tags=["SEO"])
async def robots_txt():
    """Robots.txt endpoint for search engines"""
    return {
        "content": """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /private/
Sitemap: https://plantpick.ai/sitemap.xml"""
    }

if __name__ == "__main__":
    print("🚀 Railway is running `main.py`!")
    port = int(os.getenv("PORT", 8000))  # Ensure port is integer 
    print(f"✅ Running on port: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
