# ใช้ Python 3.9 เป็น Base Image
FROM python:3.9

# ตั้งค่า Directory สำหรับ App
WORKDIR /app

# คัดลอกไฟล์ทั้งหมดไปที่ Container
COPY . /app

# ติดตั้ง Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# เปิด Port ที่ต้องใช้
EXPOSE 8000

# คำสั่งรัน FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]