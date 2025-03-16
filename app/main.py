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
    port = int(os.getenv("PORT", "8000"))  # แปลงค่า PORT ให้เป็น int
    uvicorn.run(app, host="0.0.0.0", port=port)