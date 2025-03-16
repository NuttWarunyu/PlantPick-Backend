from fastapi import APIRouter, UploadFile, File
import openai
import os

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@router.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    
    response = openai.ChatCompletion.create(
        model="gpt-4-vision-preview",
        messages=[
            {"role": "system", "content": "You are a plant identification expert."},
            {"role": "user", "content": "Identify the plant in this image."},
            {"role": "user", "content": image_bytes}
        ],
        api_key=OPENAI_API_KEY
    )
    
    plant_name = response["choices"][0]["message"]["content"]
    return {"plant_name": plant_name}