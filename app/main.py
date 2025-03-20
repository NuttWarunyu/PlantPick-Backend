import os
import uvicorn
from fastapi import FastAPI
from app.routers import upload, shopee
from app.routers import identify
from dotenv import load_dotenv

load_dotenv()  # โหลดค่าจาก .env

app = FastAPI(title="PlantPick API")

app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(shopee.router, prefix="/shopee", tags=["Shopee"])
app.include_router(identify.router, prefix="/identify", tags=["Identify"])

@app.get("/")
def root():
    return {"message": "Welcome to PlantPick API"}

if __name__ == "__main__":
    print("🚀 Railway is running `main.py`!")
    print("🔍 Environment Variables in Railway:")
    print(os.environ)  # แสดงค่าทั้งหมดที่ Railway ใช้งาน
    
    port = os.getenv("PORT", "8000")  # อ่านค่า PORT
    print(f"✅ PORT as string: {port}")  # Debug ค่า PORT (ดูว่าเป็น string หรือเปล่า)
    print(f"✅ PORT as int: {int(port)}")  # ลองแปลงเป็น int (ถ้าพัง แสดงว่า PORT ไม่ใช่ตัวเลขจริงๆ)
    
    uvicorn.run(app, host="0.0.0.0", port=int(port))  # แปลงเป็น int ก่อนใช้