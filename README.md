# 🌱 Plant Price Backend API

Backend API server สำหรับระบบจัดการราคาต้นไม้ Plant Price Management System

## 🚀 Features

- RESTful API สำหรับจัดการข้อมูลต้นไม้
- จัดการข้อมูลผู้จัดจำหน่าย
- อัปเดตราคาแบบ real-time
- CORS support สำหรับ frontend
- Error handling และ logging
- พร้อม deploy ไปยัง Railway

## 📋 API Endpoints

### Health Check
- `GET /api/health` - ตรวจสอบสถานะ API

### Plants
- `GET /api/plants` - ดึงข้อมูลต้นไม้ทั้งหมด
- `GET /api/plants/:id` - ดึงข้อมูลต้นไม้ตาม ID

### Suppliers
- `POST /api/plants/:plantId/suppliers` - เพิ่มผู้จัดจำหน่าย
- `PUT /api/plants/:plantId/suppliers/:supplierId/price` - อัปเดตราคา
- `DELETE /api/plants/:plantId/suppliers/:supplierId` - ลบผู้จัดจำหน่าย

## 🛠️ Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Start production server
npm start
```

## 🌐 Environment Variables

สร้างไฟล์ `.env` จาก `env.example`:

```bash
cp env.example .env
```

แก้ไขค่าต่างๆ ตามต้องการ:
- `PORT`: Port ของ server (default: 3001)
- `FRONTEND_URL`: URL ของ frontend สำหรับ CORS
- `NODE_ENV`: Environment (development/production)

## 🚀 Deployment

### Railway (แนะนำ)
1. สร้างโปรเจคใหม่ใน Railway
2. Connect GitHub repository
3. ตั้งค่า environment variables
4. Deploy

### Manual Deployment
```bash
# Build (if needed)
npm run build

# Start production
npm start
```

## 📊 Response Format

```json
{
  "success": true,
  "data": { ... },
  "message": "ข้อความสถานะ"
}
```

## 🔧 Development

```bash
# Install dependencies
npm install

# Start with nodemon (auto-restart)
npm run dev

# Test API
curl http://localhost:3001/api/health
```

## 🌐 Frontend Integration

Frontend repository: [Plant Price Frontend](https://github.com/NuttWarunyu/PlantPick-Frontend)

## 📞 Support

หากมีปัญหาหรือคำถาม:
1. ตรวจสอบ logs ใน Railway dashboard
2. ดู API documentation
3. สร้าง issue ใน GitHub

---

**Made with ❤️ for Thai Plant Business**
