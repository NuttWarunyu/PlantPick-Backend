# 🚀 Setup New Repository

## 1. สร้าง Repository ใหม่ใน GitHub

1. ไปที่ [GitHub](https://github.com)
2. คลิก "New repository"
3. ตั้งชื่อ: `PlantPick-Backend`
4. เลือก "Public"
5. เพิ่ม Description: "Backend API for Plant Price Management System - Node.js + Express"
6. **อย่า** check "Add a README file" (เพราะเรามีแล้ว)
7. คลิก "Create repository"

## 2. Push Code ไปยัง Repository

```bash
# Push ไปยัง repository ใหม่
git push -u origin main
```

## 3. ตั้งค่า Railway

1. ไปที่ [Railway](https://railway.app)
2. คลิก "New Project"
3. เลือก "Deploy from GitHub repo"
4. เลือก `PlantPick-Backend` repository
5. Railway จะ auto-detect และ deploy

## 4. ตั้งค่า Environment Variables

ใน Railway Dashboard:
- `NODE_ENV` = `production`
- `FRONTEND_URL` = `https://your-frontend-url.vercel.app`

## 5. ทดสอบ API

```bash
# ตรวจสอบ health check
curl https://your-railway-url.railway.app/api/health

# ดูข้อมูลต้นไม้
curl https://your-railway-url.railway.app/api/plants
```

## 6. อัปเดต Frontend

ใน Frontend repository:
- ตั้งค่า `REACT_APP_API_URL` = `https://your-railway-url.railway.app`

---

**เสร็จแล้ว! Backend พร้อมใช้งาน** 🌱
