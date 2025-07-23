# ใช้ Python 3.11 เป็น Base Image (เร็วกว่าและเสถียรกว่า)
FROM python:3.11-slim

# ตั้งค่า Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# ติดตั้ง System Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ตั้งค่า Directory สำหรับ App
WORKDIR /app

# คัดลอกไฟล์ requirements ก่อนเพื่อใช้ Docker cache
COPY requirements.txt .

# ติดตั้ง Python Dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# คัดลอกไฟล์ทั้งหมดไปที่ Container
COPY . /app

# สร้าง User ที่ไม่ใช่ root เพื่อความปลอดภัย
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# เปิด Port ที่ต้องใช้
EXPOSE 8000

# Health Check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# คำสั่งรัน FastAPI ด้วย Gunicorn (production-ready)
CMD ["gunicorn", "app.main:app", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "120"]