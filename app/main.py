import os
import uvicorn
from fastapi import FastAPI
from app.routers import upload, shopee, identify, search
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PlantPick API")

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)

origins = [
    "http://localhost:5173",
    "https://plantpick-frontend.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(shopee.router, prefix="/shopee", tags=["Shopee"])
app.include_router(identify.router, tags=["Identify"])
app.include_router(search.router, tags=["Search"])

@app.get("/")
def root():
    return {"message": "Welcome to PlantPick API"}

@app.get("/marketplace")
async def get_marketplace():
    return [
        {"name": "สนฉัตร", "price": "~200 บาท"},
        {"name": "เฟื่องฟ้า", "price": "~150 บาท"}
    ]

if __name__ == "__main__":
    print("🚀 Railway is running `main.py`!")
    print("🔍 Environment Variables in Railway:")
    print(os.environ)
    
    port = os.getenv("PORT", "8000")
    print(f"✅ PORT as string: {port}")
    print(f"✅ PORT as int: {int(port)}")
    
    uvicorn.run(app, host="0.0.0.0", port=int(port))