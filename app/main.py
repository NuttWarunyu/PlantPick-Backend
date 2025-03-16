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
    port = os.getenv("PORT", "8000")  # อ่านค่า PORT ถ้าไม่มีให้ใช้ 8000
    print(f"Running on port {port}")  # Debug log
    uvicorn.run(app, host="0.0.0.0", port=int(port))  # แปลงเป็น int ก่อนใช้