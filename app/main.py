import os
from fastapi import FastAPI
from app.routers import upload, shopee

app = FastAPI(title="PlantPick API")

app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(shopee.router, prefix="/shopee", tags=["Shopee"])

@app.get("/")
def root():
    return {"message": "Welcome to PlantPick API"}

# อ่านค่าพอร์ตจาก Environment Variable หรือใช้ค่าเริ่มต้น 8000
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))  # แปลง PORT ให้เป็น int
    uvicorn.run(app, host="0.0.0.0", port=port)