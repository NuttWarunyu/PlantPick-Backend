import os
import uvicorn
from fastapi import FastAPI
from app.routers import upload, shopee

app = FastAPI(title="PlantPick API")

app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(shopee.router, prefix="/shopee", tags=["Shopee"])

@app.get("/")
def root():
    return {"message": "Welcome to PlantPick API"}

if __name__ == "__main__":
    print("🔍 Environment Variables in Railway:")
    print(os.environ)  # แสดงค่าทั้งหมดที่ Railway ใช้งาน
    
    port = os.getenv("PORT", "8000")  # อ่านค่า PORT
    print(f"✅ Running on port: {port}")  # Debug ค่า PORT
    
    uvicorn.run(app, host="0.0.0.0", port=int(port))  # แปลงเป็น int ก่อนใช้