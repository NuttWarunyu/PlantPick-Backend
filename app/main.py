from fastapi import FastAPI
from app.routers import upload, shopee

app = FastAPI(title="PlantPick API")

app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(shopee.router, prefix="/shopee", tags=["Shopee"])

@app.get("/")
def root():
    return {"message": "Welcome to PlantPick API"}