# PlantPick - AI จัดสวน Backend API

## 🌿 เกี่ยวกับ PlantPick

**PlantPick** คือแพลตฟอร์ม **AI จัดสวน** ที่ใช้เทคโนโลยีปัญญาประดิษฐ์ล้ำสมัย เพื่อช่วยให้คุณได้สวนในฝันอย่างง่ายดาย โดยไม่ต้องมีประสบการณ์ในการจัดสวนมาก่อน

## 🚀 ฟีเจอร์หลัก

- **AI ออกแบบสวน** - ใช้ปัญญาประดิษฐ์ออกแบบสวนจากภาพบ้านจริง
- **วิเคราะห์สภาพแวดล้อม** - วิเคราะห์แสง ทิศทางลม และข้อจำกัดจากภาพถ่าย
- **เลือกสไตล์สวน** - สวนไทย สวนโมเดิร์น สวนญี่ปุ่น สวนอังกฤษ สวนทรอปิคอล
- **ประเมินงบประมาณ** - ขอรายการของและราคาประเมิน (BOM)
- **ค้นหาพรรณไม้** - ฐานข้อมูลพรรณไม้ครบครัน

## 🛠️ เทคโนโลยีที่ใช้

- **FastAPI** - Web framework สำหรับ Python
- **OpenAI API** - AI สำหรับการวิเคราะห์และออกแบบ
- **PostgreSQL** - ฐานข้อมูลหลัก
- **Redis** - Cache และ Rate Limiting
- **Docker** - Containerization
- **Railway** - Cloud Deployment

## 📦 การติดตั้ง

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis
- Docker (optional)

### การติดตั้งแบบ Local

1. **Clone Repository**
```bash
git clone https://github.com/your-username/plantpick-backend.git
cd plantpick-backend
```

2. **สร้าง Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# หรือ
venv\Scripts\activate  # Windows
```

3. **ติดตั้ง Dependencies**
```bash
pip install -r requirements.txt
```

4. **ตั้งค่า Environment Variables**
```bash
cp .env.example .env
# แก้ไขไฟล์ .env ตามการตั้งค่าของคุณ
```

5. **รัน Application**
```bash
uvicorn app.main:app --reload
```

### การติดตั้งแบบ Docker

```bash
docker build -t plantpick-backend .
docker run -p 8000:8000 plantpick-backend
```

## 🔧 API Endpoints

### Core Endpoints
- `GET /` - Root endpoint และ health check
- `GET /health` - Health check สำหรับ monitoring
- `GET /robots.txt` - Robots.txt สำหรับ search engines

### Garden Design
- `POST /garden/generate-garden` - สร้างสวนด้วย AI
- `GET /garden/check-prediction/{prediction_id}` - ตรวจสอบสถานะการสร้าง
- `POST /garden/analyze-garden` - วิเคราะห์ภาพสวน
- `POST /garden/generate-bom` - สร้างรายการของและราคา
- `GET /garden/daily-usage` - ตรวจสอบจำนวนครั้งที่เหลือ

### Plant Identification
- `POST /identify` - ระบุชนิดต้นไม้จากภาพ

### Search
- `GET /search` - ค้นหาพรรณไม้

## 🔒 Security Features

- **Rate Limiting** - จำกัดจำนวนการเรียก API
- **CORS Protection** - อนุญาตเฉพาะ domain ที่กำหนด
- **Input Validation** - ตรวจสอบข้อมูลที่รับเข้ามา
- **Error Handling** - จัดการ error อย่างปลอดภัย

## 📊 Performance Optimization

- **Gzip Compression** - บีบอัดข้อมูลเพื่อลด bandwidth
- **Database Connection Pooling** - จัดการการเชื่อมต่อฐานข้อมูลอย่างมีประสิทธิภาพ
- **Redis Caching** - Cache ข้อมูลที่ใช้บ่อย
- **Async/Await** - การประมวลผลแบบ asynchronous

## 🧪 Testing

```bash
# รัน unit tests
pytest

# รัน tests พร้อม coverage
pytest --cov=app

# รัน performance tests
pytest tests/test_performance.py
```

## 📈 Monitoring

- **Health Checks** - `/health` endpoint
- **Prometheus Metrics** - สำหรับ monitoring
- **Logging** - Structured logging
- **Error Tracking** - Error monitoring

## 🚀 Deployment

### Railway
```bash
railway login
railway link
railway up
```

### Docker
```bash
docker build -t plantpick-backend .
docker push your-registry/plantpick-backend
```

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `SUPABASE_URL` | Supabase URL | Yes |
| `SUPABASE_KEY` | Supabase key | Yes |
| `SECRET_KEY` | Secret key for JWT | Yes |
| `RATE_LIMIT_PER_MINUTE` | Rate limit per minute | No |
| `LOG_LEVEL` | Logging level | No |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Email**: support@plantpick.ai
- **Website**: https://plantpick.ai
- **Documentation**: https://docs.plantpick.ai

## 🔗 Links

- [Frontend Repository](https://github.com/your-username/plantpick-frontend)
- [API Documentation](https://api.plantpick.ai/docs)
- [Live Demo](https://plantpick.ai)

---

**PlantPick - AI จัดสวน** 🌿 | สร้างสวนในฝันด้วยปัญญาประดิษฐ์ 