from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import SessionLocal, GenerationHistory

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ManualRequestCreate(BaseModel):
    history_id: int
    customer_name: str
    customer_contact: str
    budget_range: str
    preferred_style: str
    special_requirements: Optional[str] = None

class ManualRequestResponse(BaseModel):
    request_id: int
    history_id: int
    customer_name: str
    customer_contact: str
    budget_range: str
    preferred_style: str
    special_requirements: Optional[str]
    status: str
    created_at: datetime
    image_url: str
    prompt: str

@router.post("/manual-requests", response_model=ManualRequestResponse)
async def create_manual_request(
    request: ManualRequestCreate,
    db: Session = Depends(get_db)
):
    """สร้างคำขอให้ทีมงานช่วยจัดสวน"""
    
    # ตรวจสอบว่า history_id มีอยู่จริง
    history = db.query(GenerationHistory).filter(
        GenerationHistory.history_id == request.history_id
    ).first()
    
    if not history:
        raise HTTPException(status_code=404, detail="ไม่พบประวัติการออกแบบสวน")
    
    # สร้าง manual request record
    manual_request = {
        "history_id": request.history_id,
        "customer_name": request.customer_name,
        "customer_contact": request.customer_contact,
        "budget_range": request.budget_range,
        "preferred_style": request.preferred_style,
        "special_requirements": request.special_requirements,
        "status": "pending",
        "created_at": datetime.now()
    }
    
    # TODO: เพิ่ม table สำหรับ manual_requests
    # db.add(ManualRequest(**manual_request))
    # db.commit()
    
    return ManualRequestResponse(
        request_id=1,  # TODO: ใช้ ID จริง
        image_url=history.image_url,
        prompt=history.prompt,
        **manual_request
    )

@router.get("/manual-requests", response_model=List[ManualRequestResponse])
async def get_manual_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """ดึงรายการคำขอทั้งหมด (สำหรับแอดมิน)"""
    
    # TODO: ดึงข้อมูลจาก manual_requests table
    # query = db.query(ManualRequest)
    # if status:
    #     query = query.filter(ManualRequest.status == status)
    # requests = query.all()
    
    # Mock data สำหรับทดสอบ
    return []

@router.put("/manual-requests/{request_id}/status")
async def update_request_status(
    request_id: int,
    status: str,
    admin_notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """อัปเดตสถานะคำขอ (สำหรับแอดมิน)"""
    
    # TODO: อัปเดตสถานะใน database
    # request = db.query(ManualRequest).filter(
    #     ManualRequest.request_id == request_id
    # ).first()
    # if not request:
    #     raise HTTPException(status_code=404, detail="ไม่พบคำขอ")
    # 
    # request.status = status
    # request.admin_notes = admin_notes
    # request.updated_at = datetime.now()
    # db.commit()
    
    return {"message": f"อัปเดตสถานะเป็น {status} แล้ว"}

@router.get("/admin/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    """สถิติสำหรับแอดมิน"""
    
    total_generations = db.query(GenerationHistory).count()
    today_generations = db.query(GenerationHistory).filter(
        GenerationHistory.created_at >= datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    ).count()
    
    return {
        "total_generations": total_generations,
        "today_generations": today_generations,
        "manual_requests_pending": 0,  # TODO: นับจาก database
        "manual_requests_completed": 0
    } 